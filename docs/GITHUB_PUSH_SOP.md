# GitHub 提交流程（SOP）

> **用途**：以后要往 GitHub 推代码，按这份文档走，不用重新摸索。
> **创建**：2026-10-07 ｜ **状态**：✅ 实测可用
> **关键概念**：GitHub **不接受密码认证**（2021-08 起停用），只认 **SSH 密钥**或 **PAT**。本项目全程用 SSH。

---

## 0. 一分钟速查

```bash
# 认证是否正常（应看到 "Hi JM-zhuxm!"）
ssh -T git@github.com

# phonebot-r1（主代码仓库）
cd /home/ubuntu/phonebot-r1
git remote -v                  # origin = git@github.com:JM-zhuxm/phonebot-r1.git
git add -A && git commit -m "..."
git push origin main

# Open-AutoGLM（集成 + 文档仓库）
cd /home/ubuntu/hermes-hub-forks/Open-AutoGLM
git remote -v                  # jm = git@github.com:JM-zhuxm/Open-AutoGLM.git
git switch hermes-hub-integration
git add -A && git commit -m "..."
git push jm hermes-hub-integration
```

---

## 1. 认证方式：SSH 密钥

### 1.1 用哪把钥匙

本机有 3 把与 GitHub 相关的密钥，**都在 `~/.ssh/`**（私钥 600 权限，从不外传）：

| 私钥文件 | 用途 | 关联公钥注释 |
|---|---|---|
| `~/.ssh/id_ed25519_phonebot` | **phonebot-r1** 主仓库 | `phonebot-r1-deploy@hermes-VM` |
| `~/.ssh/id_ed25519_autoglm` | **Open-AutoGLM** 集成仓库 | `open-autoglm-deploy@hermes-VM` |
| `~/.ssh/id_ed25519` | 通用备用 | `ubuntu@hermes-VM-0-5-ubuntu` |

> 🔴 **私钥绝对不能**发到聊天、不能提交进 git、不能写进文档。只用 `.pub` 公钥。

### 1.2 公钥已授权到 GitHub（2026-10-07 完成）

若某把钥匙报 `Permission denied`，说明它没被授权。补救步骤：

1. 取公钥（**只取公钥**）：
   ```bash
   cat ~/.ssh/id_ed25519_phonebot.pub
   ```
2. 在浏览器打开：<https://github.com/settings/ssh/new>
3. Title 填用途（如 `phonebot-r1-VM`），Key 粘贴上面那行**完整单行**
4. 点绿色 **Add SSH key**
5. 回本机验证：`ssh -T git@github.com` → 应出现 `Hi JM-zhuxm!`

> **指纹核对**（防止复制错行）：
> ```bash
> ssh-keygen -lf ~/.ssh/id_ed25519_phonebot.pub
> ```

### 1.3 `~/.ssh/config` 已配置

```
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_phonebot
  IdentityFile ~/.ssh/id_ed25519_autoglm
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly no
```

三把钥匙依次尝试，**任意一把被授权就能通**。

### 1.4 ssh-agent（会话重启后可能需要重载）

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519_phonebot ~/.ssh/id_ed25519_autoglm ~/.ssh/id_ed25519
ssh-add -l        # 应显示 3 把
```

---

## 2. 仓库 A：phonebot-r1（主代码，私有）

| 项 | 值 |
|---|---|
| 路径 | `/home/ubuntu/phonebot-r1` |
| 远端 | `origin` → `git@github.com:JM-zhuxm/phonebot-r1.git` |
| 可见性 | **Private** |
| 体积 | 72.79 MiB |
| 推什么 | Android App / CoreS3SE 固件 / 后端服务 |

### 日常提交流程

```bash
cd /home/ubuntu/phonebot-r1

# 1. 改代码…

# 2. 提交前必做：扫密钥（当前 + 全部历史）
git diff --cached | grep -inE "api[_-]?key[\"']?\s*[:=]\
\s*[\"'][A-Za-z0-9_-]{20,}|Bearer [A-Za-z0-9_-]{25,}" | grep -v REDACTED
git log -p --all | grep -inE "sk-[A-Za-z0-9]{20,}|AKID[A-Za-z0-9]{15,}" | head
# → 无输出才继续

# 3. 提交
git add <具体文件>          # 别无脑 -A，先看 git status
git -c user.name="Hermes Agent" -c user.email="hermes@phonebot.local" commit -F - <<'EOF'
fix(模块): 一句话说清改了什么

- 具体改动 1
- 具体改动 2
- 实测验证结果
EOF

# 4. 推送
git push origin main

# 5. 打回退点（重要改动必打）
git tag -a fix-YYYYMMDD-简述 -m "说明"
git push origin --tags
```

### 回退点标签

| 标签 | 含义 |
|---|---|
| `fix-20261007-motor-emotion-latency` | 表情修复 + motor 命令 + 重复回复 + 延时优化 |
| `baseline-20261007-1909` | 早上基线（可用的粤语单语版） |
| `multilang-wip-20261007` | 多语言 WIP（未完成，存档用） |
| `milestone-2026-10-06-servo` | PCA9685 舵机里程碑 |

回退：
```bash
git reset --hard fix-20261007-motor-emotion-latency   # 回到该成果
```

---

## 3. 仓库 B：Open-AutoGLM（集成 + 文档，公开）

| 项 | 值 |
|---|---|
| 路径 | `/home/ubuntu/hermes-hub-forks/Open-AutoGLM` |
| 远端 | `jm` → `git@github.com:JM-zhuxm/Open-AutoGLM.git` |
| 上游 | `origin` → `https://github.com/zai-org/Open-AutoGLM.git`（**只读**，HTTPS 无需认证） |
| 工作分支 | `hermes-hub-integration`（**不要动 main**，main 跟上游） |
| 推什么 | 集成脚本 + 验证脚本 + 开发计划文档包 |

### 🔴 关键原则

- **只在 `hermes-hub-integration` 分支工作**
- `main` 必须保持与上游 `origin/main` 一致，否则以后 pull 上游更新会冲突
- 定期同步上游：
  ```bash
  git fetch origin
  git rebase origin/main hermes-hub-integration   # 或 merge，看策略
  git push jm hermes-hub-integration
  ```

### 日常提交流程

```bash
cd /home/ubuntu/hermes-hub-forks/Open-AutoGLM
git switch hermes-hub-integration

# 改文件…

git add <具体文件>
git -c user.name="Hermes Agent" -c user.email="hermes@phonebot.local" commit -F - <<'EOF'
docs(plan): 一句话说明

- 改动明细
EOF

git push jm hermes-hub-integration
```

---

## 4. 🔴 提交前必做检查清单

- [ ] **扫密钥**（当前 diff + 全部历史，见 §2 步骤 2）
- [ ] `.env` / `auth.json` 未被 `git add`
- [ ] `venv/` `models/` `node_modules/` `build/` 仍在 `.gitignore`
- [ ] commit message 说清「改了什么 + 为什么」，不是「update」
- [ ] 重要改动打了 tag（可回退）
- [ ] `git status` 干净，没有漏提交的改动

---

## 5. 常见故障速查

| 现象 | 原因 | 解决 |
|---|---|---|
| `could not read Username for 'https://github.com'` | 远端配成了 **HTTPS** | 改成 SSH：`git remote set-url <name> git@github.com:...` |
| `Permission denied (publickey)` | 公钥没授权 / agent 没加载 | 见 §1.2 + §1.4 |
| `The requested URL returned error: 403` | 仓库不存在或是私有无权限 | 确认仓库名、确认 key 已授权到该账号 |
| `remote: Repository not found` | 仓库名拼错 / 权限不足 | `ssh -T git@github.com` 确认身份；核对仓库名 |
| `! [rejected] main -> main (non-fast-forward)` | 远端有新提交 | `git pull --rebase origin main` 后再推 |
| push 后发现漏了文件 | `git add` 不全 | 补一个 commit，不要 `force push`（除非确认无误） |
| `Key is already in use` | 该公钥已加过 | 无需处理，直接下一步 |

---

## 6. 绝不做的事

| ❌ 禁止 | 原因 |
|---|---|
| 把 **私钥**内容发到聊天 / 提交进 git / 写进文档 | 泄露即失去全部仓库权限 |
| 在聊天里贴 **token / PAT / 密码** | 同上，且聊天记录长期留存 |
| 往**主仓库** `main` 直接提交未经测试的代码 | 出问题无法快速回退 |
| **`force push`** 到已有 tag 的分支 | 破坏他人已拉取的引用 |
| 无脑 `git add -A` | 容易把 `.env`、临时文件、测试产物带进去 |
| 在 `Open-AutoGLM` 的 `main` 分支工作 | 会与上游冲突，失去 fork 的同步能力 |

---

## 7. 相关文件

| 文件 | 用途 |
|---|---|
| `.gitignore`（phonebot-r1） | 已忽略 `models/` `venv/` `*.onnx` `*.bak.*` `output/` `audio/*.wav` |
| `docs/hermes-hub-plan/README.md`（Open-AutoGLM） | 开发计划文档包索引 + 两仓库分工 |
| `docs/MANUAL_huina620_CONVERSION.md`（phonebot-r1） | 汇纳620 改造手册 |

---

## 8. 一句话总结

**认证靠 SSH 公钥（3 把私钥都在本机，从不外传）；两个仓库分别用 `origin`（phonebot-r1）和 `jm`（Open-AutoGLM）推送；推之前先扫密钥。**