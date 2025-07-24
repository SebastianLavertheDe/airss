# 🚀 AIRSS - 智能社交媒体RSS监控工具

一个强大的RSS监控工具，支持从多个社交媒体平台获取内容并自动推送到Notion数据库，帮你轻松追踪关注的内容创作者。

## ⚠️ 重要说明

> **🎯 VIBE CODING PROJECT**  
> 
> 此项目完全基于 **Vibe Coding**（随性编程）开发，属于实验性质的个人项目。  
> 
> ⚠️ **免责声明**: 本项目**不对任何破坏性结果负责**，包括但不限于：
> - 数据丢失或损坏
> - API 调用超限或费用产生  
> - 服务中断或不稳定
> - 配置错误导致的问题
> - 第三方服务依赖风险
> 
> 💡 **使用建议**: 
> - 仅供学习和个人使用
> - 生产环境请谨慎使用
> - 建议先在测试环境验证
> - 定期备份重要数据
> 
> 🚀 **代码质量**: 随性而写，重在功能实现，代码结构可能存在优化空间
> 
> ---


## ✨ 主要功能

### 🎯 多平台支持
- **Twitter/X**: 支持获取用户推文内容
- **微博**: 支持获取微博用户动态
- **可扩展**: 基于配置文件的平台管理，易于添加新平台

### 📡 智能RSS获取
- **多实例支持**: 自动尝试多个RSSHub实例，确保服务可用性
- **超时优化**: 60秒超时设置，适应网络波动
- **错误处理**: 详细的错误报告和自动重试机制

### 🗃️ Notion集成
- **自动推送**: 将RSS内容自动保存到Notion数据库
- **结构化存储**: 包含标题、链接、作者、发布时间、摘要等完整信息
- **按天分类**: 支持按发布时间自动分类管理
- **智能去重**: 避免重复推送相同内容

### 💾 缓存管理
- **本地缓存**: 智能缓存已处理的内容，避免重复处理
- **自动清理**: 30天自动清理过期缓存
- **增量更新**: 只推送新内容到Notion

### ⚙️ 配置管理
- **YAML配置**: 简单易读的配置文件格式
- **环境变量**: 安全的密钥管理
- **数据库ID保存**: 自动保存和重用Notion数据库ID

## 🛠️ 安装配置

### 1. 环境要求
- Python 3.8+
- 网络连接（用于访问RSSHub和Notion API）

### 2. 克隆项目
```bash
git clone <repository-url>
cd rsshubai
```

### 3. 安装依赖
```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 4. 配置环境变量
创建 `.env` 文件：
```bash
notion_key=your_notion_integration_token
```

### 5. 配置用户信息
编辑 `config.yaml` 文件：
```yaml
platforms:
  twitter:
    names:
      - id: "GitHub_Daily"
        name: "GitHub每日精选推文"
      - id: "your_twitter_user"
        name: "自定义用户名"
    rss_url:
      - "https://rsshub.pseudoyu.com/twitter/user/{username}"
      - "https://rsshub.pseudoyu.com/x/user/{username}"
      - "https://rsshub.bestblogs.dev/twitter/user/{username}"
      - "https://rsshub.bestblogs.dev/x/user/{username}"
  
  weibo:
    names:
      - id: "your_weibo_user_id"
        name: "微博用户"
    rss_url:
      - "https://rsshub.app/weibo/user/{username}"
```

## 🎮 使用方法

### 基本使用
```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行监控
python rsshubai.py
```

### 功能说明

#### 📊 监控统计
程序会显示详细的运行统计信息：
- RSS源连接状态
- 获取到的内容数量
- 新内容与缓存内容对比
- Notion推送成功率

#### 🗂️ Notion数据库结构
自动创建的Notion数据库包含以下字段：
- **标题**: RSS条目标题
- **链接**: 原文链接
- **作者**: 内容作者
- **发布时间**: 原始发布时间（支持按天分类）
- **平台**: 来源平台（TWITTER/WEIBO等）
- **用户**: 订阅的用户名
- **状态**: 处理状态（新增/已读）
- **摘要**: 内容摘要（包含HTML格式）

#### 📁 文件说明
- `config.yaml`: 用户和平台配置
- `feed_cache.json`: 本地内容缓存
- `notion_config.json`: Notion数据库配置
- `.env`: 环境变量（密钥等敏感信息）

## 🔧 高级配置

### 自定义RSSHub实例
在 `config.yaml` 中添加新的RSS源：
```yaml
platforms:
  twitter:
    rss_url:
      - "https://your-rsshub-instance.com/twitter/user/{username}"
      - "https://another-instance.com/x/user/{username}"
```

### 添加新平台
```yaml
platforms:
  新平台名称:
    names:
      - id: "用户ID"
        name: "显示名称"
    rss_url:
      - "RSS模板URL"
```

### 监控特定用户
修改 `main()` 函数：
```python
# 监控特定用户
monitor.monitor_specific_user("GitHub_Daily")

# 或监控所有配置的用户
monitor.monitor_all_users()
```

## 🎯 Notion设置

### 1. 创建Notion集成
1. 访问 [Notion Developers](https://www.notion.so/my-integrations)
2. 点击 "New integration"
3. 填写集成信息并创建
4. 复制 "Internal Integration Token"

### 2. 准备Notion页面
1. 创建一个Notion页面
2. 分享页面并复制链接
3. 从链接中提取页面ID（`/` 后的32位字符）
4. 邀请你的集成到这个页面

### 3. 配置程序
将页面ID配置到程序中（默认会自动创建数据库）

## 📝 日志和监控

### 运行日志
程序提供详细的运行日志：
```
✅ 成功加载配置文件: config.yaml
✅ Notion 客户端初始化成功
📦 缓存状态: 已缓存 10 个条目
🔍 正在尝试获取 GitHub每日精选推文
📊 总条目数: 19, 新条目: 9, 已缓存: 10
📤 Notion 推送统计: 9/9 成功
```

### 错误处理
- 网络连接问题自动重试
- RSS源不可用时切换备用源
- Notion API错误详细报告
- 配置文件格式验证

## 🔄 定时运行

### 使用cron（Linux/Mac）
```bash
# 每小时运行一次
0 * * * * cd /path/to/rsshubai && source .venv/bin/activate && python rsshubai.py

# 每天早上9点运行
0 9 * * * cd /path/to/rsshubai && source .venv/bin/activate && python rsshubai.py
```

### 使用任务计划程序（Windows）
创建Windows任务计划，定期执行脚本。

## 🛡️ 注意事项

### 安全性
- ✅ 使用环境变量存储敏感信息
- ✅ 本地缓存避免频繁API调用
- ⚠️ 不要将 `.env` 文件提交到版本控制

### 性能优化
- 💾 智能缓存机制减少重复处理
- 🔄 多实例负载均衡
- ⏱️ 合理的超时设置
- 🧹 自动清理过期数据

### 限制说明
- Notion API有速率限制
- RSSHub实例可能不稳定
- 部分平台可能有反爬虫措施

## 📋 TODO List / 开发计划

### 🤖 AI智能总结功能
- [ ] **微博风格总结** - 添加AI总结成微博风格的短文本
- [ ] **X(Twitter)风格总结** - 生成符合X平台特色的推文格式
- [ ] **小红书风格总结** - 生成小红书风格的种草笔记格式
- [ ] **智能风格选择** - 根据内容自动选择最适合的总结风格

### 📰 内容源扩展
- [ ] **微信公众号支持** - 支持总结微信公众号文章内容
- [ ] **知乎专栏** - 添加知乎专栏文章监控
- [ ] **B站动态** - 支持B站UP主动态抓取
- [ ] **GitHub Trending** - 监控GitHub热门项目
- [ ] **掘金文章** - 技术文章内容聚合
- [ ] **Medium文章** - 国外优质内容源

### 🔧 功能优化
- [ ] **批量处理优化** - 提升大量内容的处理速度
- [ ] **多语言支持** - 支持英文、日文等多语言内容
- [ ] **内容分类** - 自动为内容添加标签分类
- [ ] **重复内容检测** - 更智能的去重算法
- [ ] **定时任务管理** - 内置定时任务调度器

### 🎨 界面与体验
- [ ] **Web管理界面** - 提供可视化的配置和监控界面
- [ ] **移动端适配** - 支持手机端查看和管理
- [ ] **通知系统** - 新内容推送通知功能
- [ ] **统计报表** - 内容获取和推送的详细统计

---

💡 **贡献说明**: 欢迎提交PR实现以上功能，或提出新的功能建议！

## 📞 支持和贡献

### 问题报告
如遇到问题，请检查：
1. 网络连接是否正常
2. Notion集成权限是否正确
3. 配置文件格式是否正确
4. RSSHub实例是否可用

### 贡献代码
欢迎提交Pull Request来改进项目：
- 实现TODO List中的功能
- 添加新的社交媒体平台支持
- 优化RSS获取逻辑
- 改进Notion推送功能
- 添加新的缓存策略

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🌟 致谢

感谢以下开源项目：
- [RSSHub](https://github.com/DIYgod/RSSHub) - RSS源聚合服务
- [notion-client](https://github.com/ramnes/notion-sdk-py) - Notion API客户端
- [feedparser](https://github.com/kurtmckee/feedparser) - RSS解析库

---

⭐ 如果这个项目对你有帮助，请给个Star支持一下！ 