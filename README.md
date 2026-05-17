<p align="center">
  <img src="icons/icon.png" alt="蓝色小嗵" width="96" />
</p>

# <p align="center">蓝色小嗵</p>

<p align="center"><strong>一只住在你桌面上的蓝色小精灵，能聊天、有记忆、会成长。</strong></p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-blue" />
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" />
  <img src="https://img.shields.io/badge/license-MIT-green" />
</p>

TA 会跟着你的鼠标转眼睛，你喂 TA，TA 会高兴；你忘了 TA，TA 会饿。TA 能感知你的键盘节奏并做出反应，还能趴在你的窗口上方跟着你一起工作。配置好接口后，和 TA 说话，TA 会记住你说过的事。

---

## 功能

### 桌面陪伴

- 常驻桌面，不遮挡、不打扰
- idle 状态下眼睛实时跟随鼠标光标
- 可拖拽抛出，带重力下落和边界回弹
- 自动吸附到打开的窗口顶部，跟随窗口移动
- 感知键盘输入节奏：打字时会抖动欢呼，高速输入有专属反应
- 15 种动作动画：行走、摸头、吃东西、睡觉、唤醒、玩耍、变猫猫、学习、拖拽、吸附、坠落、着陆等

### 养成系统

- 四项属性：饱食度、心情值、体力值、亲密度，随时间自然衰减
- 等级与经验值，陪伴自动积累
- 每日签到，连续签到加成
- 每日 7 个任务（从 18 个任务池中按日期轮换），涵盖喂食、摸头、玩耍、在线、学习、聊天
- 9 项成就，解锁获得金币奖励
- 金币商店：7 种道具（苹果、蛋糕、糖果、咖啡、玩偶、经验星、礼物盒），各有专属动画和属性效果
- 背包系统，购买的道具随时可用

### 你的朋友

- 支持配置 API 接口相关信息（URL + Key + 模型名称），一次设置即可
- 对话以气泡形式实时显示在桌宠旁边
- 对话内容自动触发匹配动画（聊到"吃"会播放吃东西动画等）
- 根据时段（早/午/晚/夜）、心情、动作自动生成不同台词

### 知识中心

- 独立的知识中心窗口，统一管理桌宠的所有记忆
- 记忆按来源自动分类：对话提取、文档导入、网络爬取、手动添加
- 角色设定文档永久生效，可直接在界面内编辑，也可导入外部 `.txt` 文档
- 一键网页信息搜集：支持 B 站视频、百度百科、通用网页，抓取后自动入库
- 关键字搜索与分类筛选

### 便携存储

- 所有个人数据存放在程序目录下的 `geren/` 文件夹
- 解压到哪里数据就跟到哪里，不占用 C 盘空间
- 首次启动自动从旧版本路径迁移数据

---

## 快速开始

### 环境要求

- Windows 10 / 11
- Python 3.10+

### 安装与运行

```bash
pip install PyQt5 pynput
python main.py
```

### 首次使用

1. 启动后右键桌宠 → **个人中心**
2. 面板自动跳转到「设置」页
3. 填写 API 地址和 Key，点击「测试连接」
4. 切换到「聊天」页，开始和 TA 说话

---

## 打包为 EXE

可使用 PyInstaller 打包为单个可执行文件，方便分发：

```bash
pip install pyinstaller
python -m PyInstaller tools/build_onefile.spec --noconfirm
```

打包后的 `dist/xiaotong.exe` 即为完整程序，双击运行，无需 Python 环境。

---

## 数据存储

```
desktop-pet/
├── geren/                        # 用户数据（自动创建）
│   ├── chat_config.json          # API 配置
│   ├── chat_memory.json          # 聊天记录与记忆
│   ├── pet_save.json             # 宠物存档
│   ├── game_data.json            # 签到、任务、成就、背包
│   ├── default_persona.txt       # 角色设定文档（可编辑）
│   └── avatar_custom.png         # 自定义头像
└── data/
    └── default_persona.txt       # 内置角色设定（首次启动复制到 geren/）
```

---

## 项目结构

```
src/
├── pet_state.py              # 宠物状态与属性管理
├── pet_animator.py           # 动画状态机与帧计时
├── pet_renderer_sprite.py    # 精灵渲染与帧序列加载
├── bubble_widget.py          # 桌面气泡弹窗
├── input_monitor.py          # 全局键盘/鼠标事件监听
├── chat_service.py           # 接口调用与记忆提取
├── game_systems.py           # 签到、任务、成就、商店、背包
├── status_panel.py           # 个人中心面板（7 个标签页）
├── knowledge_hub.py          # 知识中心窗口
├── snap_system.py            # 窗口吸附检测
├── web_crawler.py            # 网页内容抓取
├── pak_loader.py             # 动画资源包加载
└── user_data.py              # 数据路径管理与旧版迁移
```

---

## 技术栈

- **Python 3.10+**
- **PyQt5** — 界面与渲染
- **pynput** — 全局键盘/鼠标监听
- **Win32 API (ctypes)** — 窗口枚举、DPI 感知、吸附检测
- **urllib / ssl** — 标准库 HTTP，无第三方网络依赖

---
