# git 速查（DataRobot 项目）

> 面向本项目的单人开发场景：**两个本地仓库、没有远程**、在意可回退。
> 这里只列真正用得到的，不追求完整。

---

## 0. 本项目有两个仓库（互不相识）

| | 位置 | 说明 |
|---|---|---|
| 桌面 | `C:\Users\yinbaofeng\Desktop\xuniceshi_ws\.git\` | 开发副本（Windows，你用工具编辑的地方） |
| 板子 | `/home/admin/xuniceshi_ws/.git/` | 真机（`ssh admin@192.168.222.132`） |

两边 `git remote -v` **都是空的** —— 意思是两个仓库**记各自的账，互不知道对方存在**：
桌面在 `dce7418`，板子在 `f27f3f7`。所以"同步"要靠 rsync 或手配 remote，`git push` 现在没地方推。

**命令两边完全一样**，只是要在对应的工作区里执行。

---

## 1. 日常查看（只读，随便用）

```bash
git status                      # 现在有哪些改动（最常用）
git status --short              # 紧凑版
git log --oneline -10           # 最近 10 条提交
git log --oneline --graph --all # 带分支图
git diff                        # 我改了什么（还没 add）
git diff --staged               # 我 add 了什么
git show <sha>                  # 某个提交具体改了什么
git ls-files --eol              # 换行符状态（i/lf w/lf 表示 LF，板子上要这个）
```

## 2. 提交

```bash
git add <文件>                  # 暂存指定文件
git add -A                      # 暂存所有改动（含删除）
git commit -m "说明"            # 提交
git commit --amend              # 修补**最近一次**提交（改信息 / 补漏掉的文件）
```

> ⚠️ 本项目提交信息结尾要带署名行（见已有的 `dce7418`）。

---

## 3. 回退 —— 先问：**改动现在处于哪个状态？**

| 改动在哪 | 我想… | 命令 |
|---|---|---|
| 改了，**还没 add** | 丢弃某个文件 | `git restore <文件>` |
| 改了，**还没 add** | 丢弃全部 | `git restore .` |
| **add 了**，还没 commit | 从暂存区拿出（改动保留） | `git restore --staged <文件>` |
| **commit 了** | 改提交信息 / 补文件 | `git commit --amend` |
| **commit 了** | 撤销提交，**保留**改动 | `git reset --soft HEAD~1` |
| **commit 了** | 撤销提交，**丢弃**改动 | `git reset --hard HEAD~1` |
| **commit 了**，且已给别人 | 安全撤销（生成反向提交） | `git revert <sha>` |
| 想回到很久前的某个提交 | 工作区变成那时的样子 | `git reset --hard <sha>` |
| 只是想**看看**旧提交 | 临时切过去（不动分支） | `git switch --detach <sha>` |
| 删了**已跟踪**的文件 | 找回 | `git restore <文件>` |
| 删了**未跟踪**的文件 | ❌ **git 救不回** | 只能靠快照 / 备份 |
| 提交"不见了" | 用 reflog 找 | `git reflog` |

### 三个 `reset` 的区别（最容易搞混）

```bash
git reset --soft HEAD~1     # 撤销提交，改动**留在暂存区**（"我只是想重新提交"）
git reset --mixed HEAD~1    # 撤销提交，改动**留在工作区**（默认，等于取消 add）
git reset --hard HEAD~1     # 撤销提交，改动**全部丢弃**  ⚠️ 不可逆
```

记忆法：**`soft` 保得最多，`hard` 全丢。**

### `reset` vs `revert` —— 别用错

| | 干什么 | 历史会怎样 | 什么时候用 |
|---|---|---|---|
| `reset` | **改写**历史，像那个提交没发生过 | 提交从历史里消失 | 只有自己用（本项目现状） |
| `revert` | **新增**一个提交，反向抵消之前的改动 | 历史完整保留 | 已推给别人，不能改写 |

---

## 4. reflog —— 最后的安全网

**git 几乎不会真的丢东西。** 只要提交过、甚至只是 add 过，reflog 都记得：

```bash
git reflog                     # 所有操作流水账
git reset --hard HEAD@{2}      # 回到两步之前的状态
git switch -c rescue <sha>     # 把一个"不见了"的提交救回成新分支
```

> 实例：本项目 `5e2b571` 被 `commit --amend` 覆盖后不再属于任何分支，
> 但它仍在对象库里 —— 用 reflog 就能捞回来。

---

## 5. ⚠️ 危险命令（用之前必须知道）

| 命令 | 危险在哪 | 安全用法 |
|---|---|---|
| `git reset --hard` | 丢弃未提交的改动，**不可逆** | 先 `git stash` 或 `git diff > /tmp/x.patch` |
| `git clean -fd` | **删掉所有未跟踪文件**，git 救不回 | **先 `git clean -n` 预演** |
| `git restore .` | 丢弃全部未 add 的改动 | 先 `git diff` 看一眼 |
| `git push --force` | 覆盖远端历史 | 本项目暂时用不到 |

## 6. git 的边界（很重要，本项目踩过）

**git 只管它跟踪的文件。**

| 情况 | git 能救回来吗 |
|---|---|
| 已跟踪的文件被改 / 被删 | ✅ `git restore <文件>` |
| `gitignore` 里的文件（`*.bak*`、`frames_*`、`build/`、`log/`） | ❌ **git 不知道它们存在过** |
| 从未 `git add` 过的文件 | ❌ 同上 |

**2026-09-29 的实例**：一次 `rsync --delete` 删掉板子上 53 个文件，其中
`.bak` / `frames_*.pdf` / `src/src/` 全是 gitignore 或未跟踪的 ——
**git 完全救不回来**，只能靠用户自己的备份。

👉 这就是为什么本项目额外有 **`board_tools/board_snapshot.sh`**（打快照）。
**动板子之前先打快照，别只依赖 git。**

---

## 7. 本项目常见场景

### 标定完改了 `gear_ratio`，发现改错了想退回去

```bash
cd ~/xuniceshi_ws

git diff src/datarobot_base/config/base_driver.yaml     # 1. 先看改了什么
git restore src/datarobot_base/config/base_driver.yaml  # 2. 丢弃改动
git status --short                                      # 3. 确认
```

> ⚠️ 改完 `config/*.yaml` 记得 `colcon build --packages-select datarobot_base`，否则不生效。

### 板子上实验做乱了，回到今早的检查点

```bash
cd ~/xuniceshi_ws
git reset --hard f27f3f7

# 或者整包还原（连 gitignore 的文件一起）
tar xzf ~/ws_snapshots/ws_20260929_091553.tar.gz -C ~
```

### 想看看板子和桌面到底差在哪

两边都没有 remote，所以不能直接 `git diff` 对比。可以：
```bash
# 分别在两边跑，对比输出
git log --oneline -3
git status --short
```

---

## 8. 两个好习惯

1. **危险命令前先预演**
   - `git clean -n`（看会删什么）→ 确认了再去掉 `-n`
   - `git diff` → 确认了再 `git restore`

2. **看不懂就 `--help`**
   ```bash
   git reset --help
   ```

> 想了解 `.git` 目录内部长什么样（HEAD / refs / objects / reflog 各是什么），
> 见本目录 README 的"相关文档"，或直接问。
