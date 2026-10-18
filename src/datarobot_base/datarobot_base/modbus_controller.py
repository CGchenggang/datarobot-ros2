"""
Modbus RTU communication module for dual-axis motor driver.

Protocol: Modbus RTU, 115200bps, 8N1
Station ID: 0x01
A-axis (Left wheel): F0.x.xxx registers (0x2xxx)
B-axis (Right wheel): F1.x.xxx registers (0x3xxx)
"""

import serial
import struct
import threading
import time
from typing import Tuple, Optional


class ModbusController:
    """Modbus RTU controller for dual-axis motor driver."""

    # Register addresses
    REG_A_ENABLE = 0x2100      # F0.1.000 - A axis enable
    REG_B_ENABLE = 0x3100      # F1.1.000 - B axis enable
    REG_A_SPEED = 0x2318       # F0.3.018 - A axis speed (rpm)
    REG_B_SPEED = 0x3318       # F1.3.018 - B axis speed (rpm)
    REG_A_ACTUAL_SPEED = 0x5000  # D0.00 - A axis actual speed
    REG_B_ACTUAL_SPEED = 0x5100  # D1.00 - B axis actual speed

    # Function codes
    FUNC_READ_HOLDING = 0x03
    FUNC_WRITE_SINGLE = 0x06
    FUNC_DUAL_READ = 0x43
    FUNC_DUAL_WRITE = 0x44

    def __init__(self, port: str = '/dev/datarobot_base', baudrate: int = 115200,
                 slave_id: int = 0x01, timeout: float = 0.1, logger=None):
        """
        Initialize Modbus controller.

        Args:
            port: Serial port device（默认是 udev 固定名，见
                config/udev/99-datarobot.rules）
            baudrate: Communication baudrate (default 115200)
            slave_id: Modbus slave ID (default 0x01)
            timeout: Serial timeout in seconds
            logger: Optional ROS2 logger for debug output
        """
        self.port = port
        self.baudrate = baudrate
        self.slave_id = slave_id
        self.timeout = timeout
        self.serial = None
        self.lock = threading.Lock()
        self.logger = logger
        self.write_only = False  # Write-only mode (skip reading responses)

    def connect(self) -> bool:
        """Open serial connection."""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            time.sleep(0.2)  # Wait for port and RS485 adapter to stabilize
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            return True
        except Exception as e:
            print(f"Failed to open serial port {self.port}: {e}")
            return False

    def set_write_only(self, enabled: bool):
        """Enable or disable write-only mode (skip reading responses)."""
        self.write_only = enabled
        if self.logger:
            self.logger.info(f"Write-only mode: {enabled}")

    def disconnect(self):
        """Close serial connection."""
        if self.serial and self.serial.is_open:
            self.serial.close()

    def _calc_crc16(self, data: bytes) -> int:
        """Calculate Modbus CRC-16."""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def _build_frame(self, func_code: int, data: bytes) -> bytes:
        """Build Modbus frame with CRC."""
        frame = bytes([self.slave_id, func_code]) + data
        crc = self._calc_crc16(frame)
        frame += struct.pack('<H', crc)  # Little-endian CRC
        return frame

    def _send_receive(self, frame: bytes, expected_len: int, debug: bool = False) -> Optional[bytes]:
        """Send frame and receive response."""
        with self.lock:
            if not self.serial or not self.serial.is_open:
                return None

            try:
                if debug and self.logger:
                    tx_hex = ' '.join(f'{b:02X}' for b in frame)
                    self.logger.info(f"TX: {tx_hex} (write_only={self.write_only})")

                self.serial.write(frame)

                # 只写模式：完全不读应答。
                # ⚠️ 这里必须返回 None，不能返回占位缓冲。早期版本返回
                # b'\x00' * expected_len，但该字节串是**真值**，调用方 dual_read()
                # 会照常解析出 (0, 0)，看起来就像"电机转速为零"——
                # 结果是 /odom 恒停在原点（电机照转，里程计不动）。
                if self.write_only:
                    time.sleep(0.01)  # 确保命令已发出
                    if debug and self.logger:
                        self.logger.info("Write-only mode: skipping response")
                    return None

                # Small delay for RS485 direction switching
                time.sleep(0.005)  # 5ms

                # Collect the response until complete or the deadline passes,
                # instead of assuming it has arrived after a fixed delay.
                deadline = time.time() + self.timeout
                response = b''
                while len(response) < expected_len and time.time() < deadline:
                    chunk = self.serial.read(expected_len - len(response))
                    if chunk:
                        response += chunk

                if debug and self.logger:
                    rx_hex = ' '.join(f'{b:02X}' for b in response)
                    self.logger.info(f"RX: {rx_hex} (expected {expected_len}, got {len(response)})")

                if len(response) < expected_len:
                    if debug and self.logger:
                        self.logger.warn(f"Response too short: expected {expected_len}, got {len(response)}")
                    return None

                # Verify CRC
                received_crc = struct.unpack('<H', response[-2:])[0]
                calc_crc = self._calc_crc16(response[:-2])
                if received_crc != calc_crc:
                    msg = f"CRC error: received {received_crc:04X}, calculated {calc_crc:04X}"
                    if self.logger:
                        self.logger.error(msg)
                    else:
                        print(msg)
                    return None

                return response
            except Exception as e:
                msg = f"Communication error: {e}"
                if self.logger:
                    self.logger.error(msg)
                else:
                    print(msg)
                return None

    def write_single_register(self, reg_addr: int, value: int) -> bool:
        """Write single register (function 0x06)."""
        data = struct.pack('>HH', reg_addr, value & 0xFFFF)
        frame = self._build_frame(self.FUNC_WRITE_SINGLE, data)
        response = self._send_receive(frame, 8)
        return response is not None

    def read_holding_register(self, reg_addr: int) -> Optional[int]:
        """Read single holding register (function 0x03)."""
        data = struct.pack('>HH', reg_addr, 1)  # Read 1 register
        frame = self._build_frame(self.FUNC_READ_HOLDING, data)
        response = self._send_receive(frame, 7)

        if response:
            value = struct.unpack('>H', response[3:5])[0]
            return value
        return None

    def dual_write(self, addr1: int, addr2: int, value1: int, value2: int, debug: bool = False) -> bool:
        """Dual write (function 0x44) - write two registers simultaneously."""
        addr1_h = (addr1 >> 8) & 0xFF
        addr1_l = addr1 & 0xFF
        addr2_h = (addr2 >> 8) & 0xFF
        addr2_l = addr2 & 0xFF
        val1_h = (value1 >> 8) & 0xFF
        val1_l = value1 & 0xFF
        val2_h = (value2 >> 8) & 0xFF
        val2_l = value2 & 0xFF

        data = bytes([addr1_h, addr1_l, addr2_h, addr2_l,
                      val1_h, val1_l, val2_h, val2_l])
        frame = self._build_frame(self.FUNC_DUAL_WRITE, data)
        response = self._send_receive(frame, 12, debug=debug)

        # In write_only mode, always return success if no exception
        if self.write_only:
            return True

        return response is not None

    def dual_read(self, addr1: int, addr2: int) -> Optional[Tuple[int, int]]:
        """Dual read (function 0x43) - read two registers simultaneously."""
        addr1_h = (addr1 >> 8) & 0xFF
        addr1_l = addr1 & 0xFF
        addr2_h = (addr2 >> 8) & 0xFF
        addr2_l = addr2 & 0xFF

        data = bytes([addr1_h, addr1_l, addr2_h, addr2_l])
        frame = self._build_frame(self.FUNC_DUAL_READ, data)
        response = self._send_receive(frame, 12)

        if response:
            val1 = struct.unpack('>H', response[6:8])[0]
            val2 = struct.unpack('>H', response[8:10])[0]
            # Convert to signed int16
            if val1 & 0x8000:
                val1 = val1 - 0x10000
            if val2 & 0x8000:
                val2 = val2 - 0x10000
            return (val1, val2)
        return None

    def enable_motors(self, enable: bool = True, retries: int = 3,
                      debug: bool = False) -> bool:
        """
        Enable or disable both motors.

        The first transaction after opening the port is sometimes lost while the
        RS485 adapter settles, so retry a few times before giving up.
        """
        value = 1 if enable else 0
        for attempt in range(retries):
            if self.dual_write(self.REG_A_ENABLE, self.REG_B_ENABLE,
                               value, value, debug=debug):
                return True
            if attempt < retries - 1:
                time.sleep(0.05)
        return False

    def set_motor_speeds(self, left_rpm: int, right_rpm: int, debug: bool = False) -> bool:
        """
        Set motor speeds in RPM.

        Args:
            left_rpm: Left motor speed (-32768 to 32767 rpm)
            right_rpm: Right motor speed (-32768 to 32767 rpm)
        """
        # Convert negative values to unsigned 16-bit
        left_val = left_rpm if left_rpm >= 0 else (0x10000 + left_rpm)
        right_val = right_rpm if right_rpm >= 0 else (0x10000 + right_rpm)

        if debug and self.logger:
            self.logger.info(f"Setting speeds: left={left_rpm} RPM (0x{left_val:04X}), right={right_rpm} RPM (0x{right_val:04X})")

        return self.dual_write(self.REG_A_SPEED, self.REG_B_SPEED,
                              left_val & 0xFFFF, right_val & 0xFFFF, debug=debug)

    def get_motor_speeds(self) -> Optional[Tuple[int, int]]:
        """Get actual motor speeds in RPM."""
        return self.dual_read(self.REG_A_ACTUAL_SPEED, self.REG_B_ACTUAL_SPEED)


if __name__ == '__main__':
    # 独立硬件自测（脱离 ROS2 直接验证串口通信和电机方向）。
    #   python3 modbus_controller.py [串口设备]
    # ⚠️ 跑之前务必把驱动轮架空。
    import sys
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/datarobot_base'
    controller = ModbusController(port)
    if controller.connect():
        print("Connected to Modbus controller")

        # Enable motors
        if controller.enable_motors(True):
            print("Motors enabled")

        # Set speeds
        if controller.set_motor_speeds(100, 100):
            print("Speed set to 100 RPM")

        time.sleep(1)

        # Read actual speeds
        speeds = controller.get_motor_speeds()
        if speeds:
            print(f"Actual speeds: Left={speeds[0]} RPM, Right={speeds[1]} RPM")

        # Stop motors
        controller.set_motor_speeds(0, 0)
        time.sleep(0.5)
        controller.enable_motors(False)

        controller.disconnect()
