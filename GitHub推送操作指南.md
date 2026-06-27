# 具身智能学习项目 - GitHub推送操作指南

## 一、已完成配置（本地自动完成）

### 1. Git全局用户配置
```bash
git config --global user.name "cugzhaolei"
git config --global user.email "1552570872@qq.com"
```

### 2. SSH Key生成
已生成新的ED25519密钥对：
- 私钥：`C:\Users\admin\.ssh\id_ed25519_github`
- 公钥：`C:\Users\admin\.ssh\id_ed25519_github.pub`

公钥内容：
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILuMQTENsZIkYB4Jee5OTxQKAEY6E3uhWmI1B/LdTKCF 1552570872@qq.com
```

### 3. SSH Config配置
已创建 `C:\Users\admin\.ssh\config`，让GitHub连接使用新key：
```
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github
```

---

## 二、需要你在网页上手动操作的步骤

### 步骤1：在GitHub添加SSH公钥

1. 打开浏览器，登录 GitHub 账号：https://github.com/login
   - 如果没有账号，先去 https://github.com/signup 注册
2. 点击右上角头像 → **Settings**
3. 左侧菜单选择 **SSH and GPG keys**
4. 点击 **New SSH key**
5. 填写信息：
   - **Title**：随意填，如 `My-Windows-PC`
   - **Key type**：选择 `Authentication Key`
   - **Key**：粘贴以下公钥内容（复制整行）：

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILuMQTENsZIkYB4Jee5OTxQKAEY6E3uhWmI1B/LdTKCF 1552570872@qq.com
```

6. 点击 **Add SSH key**
7. 可能需要输入GitHub密码确认

### 步骤2：在GitHub创建新仓库

1. 登录GitHub后，点击右上角 **+** → **New repository**
2. 填写仓库信息：
   - **Repository name**：`2000_Embody`（或你喜欢的名字）
   - **Description**：`具身智能学习 - MiniVLA实战教程与SO101仿真`
   - **Public**（建议公开，方便学习交流）
   - **不要**勾选 "Add a README file"、".gitignore"、"License"（本地已有内容）
3. 点击 **Create repository**
4. 记下仓库地址，格式类似：`git@github.com:cugzhaolei/2000_Embody.git`

---

## 三、验证SSH连接

在完成网页端配置后，打开终端验证：

```bash
ssh -T git@github.com
```

如果看到 `Hi cugzhaolei! You've successfully authenticated...` 说明配置成功。

---

## 四、推送项目到GitHub（我来帮你执行）

确认SSH连接成功后，执行以下操作：

```bash
# 1. 初始化本地仓库
cd C:\Users\admin\Desktop\dev\2000_Embody
git init

# 2. 添加所有文件（已排除隐私信息）
git add .

# 3. 首次提交
git commit -m "Initial commit: 具身智能学习项目"

# 4. 添加远程仓库
git remote add origin git@github.com:cugzhaolei/2000_Embody.git

# 5. 推送到GitHub
git push -u origin main
```

---

## 五、隐私保护说明

以下内容已被排除，不会被提交到GitHub：

| 排除项 | 原因 |
|--------|------|
| `CUsersadmin/` 目录 | 包含conda/miniconda本地配置 |
| `.env` 文件 | 可能包含API密钥和Token |
| `__pycache__/` | Python缓存文件 |
| `.ssh/` 目录 | 私钥和配置文件 |
| `*.egg-info/` | Python打包信息 |
| `.vscode/` | IDE个人配置 |
| `.idea/` | IDE个人配置 |
| `wandb/` | 训练日志可能含敏感信息 |
| `data/`、`cache/` | 大型数据集文件 |
| `rollouts/` | 仿真视频文件 |

---

## 六、常见问题

### Q: SSH连接被拒绝？
- 确认已在GitHub网页端添加了SSH公钥
- 检查公钥是否完整复制（以 `ssh-ed25519` 开头）
- 运行 `ssh -vT git@github.com` 查看详细错误信息

### Q: push被拒绝？
- 确认仓库名和用户名正确
- 如果仓库不为空，先 `git pull --rebase origin main`

### Q: 如何切换回原来的Git账号？
```bash
git config --global user.name "three_st"
git config --global user.email "270828191@qq.com"
# 修改SSH config指向原来的key
```
