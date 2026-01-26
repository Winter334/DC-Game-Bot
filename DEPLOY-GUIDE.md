# 🚀 GitHub + 1Panel VPS 部署指南

本指南将帮助你将 Discord Game Center Bot 推送到 GitHub 并在安装了 1Panel 的 Ubuntu VPS 上部署。

## 📋 前置条件

- GitHub 账号
- 已安装 Git 的本地电脑
- 已安装 1Panel 的 Ubuntu VPS
- Discord Bot Token

---

## 第一步：推送到 GitHub

### 1.1 创建 GitHub 仓库

1. 登录 [GitHub](https://github.com)
2. 点击右上角 **+** → **New repository**
3. 填写仓库信息：
   - Repository name: `discord-game-center`
   - Description: `Discord游戏中心Bot`
   - 选择 **Private**（推荐，因为可能涉及敏感配置）
4. **不要**勾选 "Add a README file"（我们已有）
5. 点击 **Create repository**

### 1.2 初始化本地 Git 仓库并推送

在项目目录下打开终端/命令提示符，执行：

```bash
# 进入项目目录
cd discord-game-center

# 初始化Git仓库
git init

# 添加所有文件
git add .

# 创建首次提交
git commit -m "Initial commit: Discord Game Center Bot"

# 添加远程仓库（替换为你的GitHub用户名）
git remote add origin https://github.com/你的用户名/discord-game-center.git

# 推送到GitHub
git branch -M main
git push -u origin main
```

### 1.3 验证

访问你的 GitHub 仓库页面，确认所有文件已上传。

> ⚠️ **安全提醒**：`.env` 文件已在 `.gitignore` 中，不会被推送，这是正确的做法。

---

## 第二步：在 VPS 上部署

### 2.1 通过 1Panel 安装 Docker

1. 登录 1Panel 面板（通常是 `http://你的VPS-IP:端口`）
2. 进入 **应用商店**
3. 搜索并安装 **Docker**（如果尚未安装）
4. 等待安装完成

### 2.2 SSH 连接到 VPS

使用 SSH 工具（如 PuTTY、Termius 或终端）连接到 VPS：

```bash
ssh root@你的VPS-IP
```

### 2.3 克隆项目

```bash
# 创建应用目录
mkdir -p /opt/apps
cd /opt/apps

# 克隆你的GitHub仓库
git clone https://github.com/你的用户名/discord-game-center.git

# 进入项目目录
cd discord-game-center
```

> 💡 如果是私有仓库，需要输入 GitHub 用户名和 Personal Access Token（不是密码）。
> 创建 Token：GitHub → Settings → Developer settings → Personal access tokens → Generate new token

### 2.4 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置文件
nano .env
```

在编辑器中修改：

```
BOT_TOKEN=你的Discord_Bot_Token
```

按 `Ctrl+X`，然后按 `Y`，再按 `Enter` 保存退出。

### 2.5 使用 Docker Compose 启动

```bash
# 启动Bot（后台运行）
docker compose up -d

# 查看运行状态
docker compose ps

# 查看日志
docker compose logs -f
```

按 `Ctrl+C` 退出日志查看。

---

## 第三步：通过 1Panel 管理（可选）

### 3.1 在 1Panel 中查看容器

1. 进入 1Panel → **容器**
2. 你会看到 `game-center-bot` 容器
3. 可以在这里：
   - 查看容器状态
   - 查看日志
   - 停止/重启容器
   - 进入容器终端

### 3.2 1Panel Docker Compose 管理

1. 进入 1Panel → **容器** → **编排**
2. 点击 **创建编排**
3. 名称：`game-center-bot`
4. 路径：`/opt/apps/discord-game-center`
5. 这样可以通过 1Panel 图形界面管理

---

## 📝 常用维护命令

### 更新Bot代码

当你更新了代码并推送到 GitHub 后：

```bash
cd /opt/apps/discord-game-center

# 拉取最新代码
git pull

# 重新构建并启动
docker compose build
docker compose up -d
```

### 查看日志

```bash
# 实时查看日志
docker compose logs -f

# 查看最近100行日志
docker compose logs --tail 100
```

### 重启Bot

```bash
docker compose restart
```

### 停止Bot

```bash
docker compose down
```

### 完全重建（清除缓存）

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## 🔧 故障排除

### 问题：Bot无法启动

1. 检查Token是否正确：

   ```bash
   cat .env
   ```

2. 查看详细日志：

   ```bash
   docker compose logs
   ```

### 问题：权限错误

```bash
# 修复权限
sudo chown -R $USER:$USER /opt/apps/discord-game-center
chmod +x start.sh
```

### 问题：端口被占用

Bot不需要开放端口，如果遇到端口问题，检查是否有其他服务冲突。

### 问题：数据库丢失

数据保存在 `./data/` 目录，确保该目录存在并有写入权限：

```bash
mkdir -p data
chmod 755 data
```

---

## 🔐 安全建议

1. **使用私有仓库** - 避免泄露代码逻辑
2. **不要提交 .env** - 已在 .gitignore 中配置
3. **定期更新依赖** - 修复安全漏洞
4. **设置防火墙** - 1Panel自带防火墙功能
5. **定期备份数据** - 备份 `data/games.db`

---

## 📊 快速命令参考

| 操作     | 命令                                                       |
| -------- | ---------------------------------------------------------- |
| 启动     | `docker compose up -d`                                     |
| 停止     | `docker compose down`                                      |
| 重启     | `docker compose restart`                                   |
| 查看状态 | `docker compose ps`                                        |
| 查看日志 | `docker compose logs -f`                                   |
| 更新代码 | `git pull && docker compose build && docker compose up -d` |

---

完成以上步骤后，你的 Bot 就会在 VPS 上稳定运行了！🎉
