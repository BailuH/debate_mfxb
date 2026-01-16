# 数字法庭Demo

基于LangGraph的法庭辩论模拟系统演示版本。

## 快速开始

### 1. 安装依赖

```bash
# 使用uv（推荐）
uv sync

# 或使用pip
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```
# OpenAI API配置（如果使用OpenAI）
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1

# DeepSeek API配置
OPENAI_API_KEY=your_deepseek_api_key
OPENAI_API_BASE=https://api.deepseek.com/v1
```

### 3. 启动服务

```bash
python main.py
```

服务器将在 `http://localhost:8000` 启动。

### 4. 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API使用示例

### 创建法庭会话

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "case_info": "张三于2023年1月向李四借款10万元，约定3个月归还，但至今未还。李四持有张三签名的借条。",
    "case_evidence": [
      {
        "speaker": "原告律师",
        "content": "借条照片：显示张三于2023年1月15日借款10万元，约定2023年4月15日归还"
      }
    ],
    "human_role": "被告律师"
  }'
```

响应：
```json
{
  "session_id": "court_a1b2c3d4",
  "status": "created",
  "current_phase": "开庭阶段",
  "current_speaker": "原告律师"
}
```

### 查询会话状态

```bash
curl http://localhost:8000/api/sessions/court_a1b2c3d4
```

### WebSocket连接

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/court_a1b2c3d4?role=被告律师');

ws.onopen = () => {
  console.log('WebSocket连接已建立');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('收到消息:', message);

  switch (message.event) {
    case 'debate_update':
      // 辩论更新
      console.log('新消息:', message.data.new_message);
      break;

    case 'human_input_required':
      // 需要人类输入
      console.log('需要输入:', message.data.prompt);
      // 显示输入框，用户输入后发送：
      // ws.send(JSON.stringify({
      //   event: 'human_input',
      //   data: { content: '用户输入的内容', role: '被告律师' }
      // }));
      break;

    case 'debate_ended':
      // 辩论结束
      console.log('辩论已结束');
      break;
  }
};

ws.onclose = () => {
  console.log('WebSocket连接已关闭');
};
```

## WebSocket事件

### 服务器推送事件

1. **debate_update**: 辩论更新
2. **human_input_required**: 需要人类输入
3. **debate_ended**: 辩论结束
4. **status_update**: 状态更新
5. **error**: 错误消息

### 客户端发送事件

1. **human_input**: 提交人类输入
2. **next_step**: 请求继续推进（AI模式）
3. **ping**: 心跳检测

## 项目结构

```
src/
├── agent.py              # 智能体定义
├── state.py              # 状态定义
├── workflow.py           # 工作流定义
├── prompt.py             # 提示词
├── llmconfig.py          # LLM配置
├── api/
│   ├── main.py           # FastAPI应用入口
│   ├── routes/
│   │   ├── sessions.py   # 会话管理API
│   │   └── websocket.py  # WebSocket端点
│   └── websocket/
│       └── manager.py    # WebSocket连接管理
├── services/
│   └── court_service.py  # 法庭服务层
└── schemas/
    ├── session.py        # Pydantic模型：会话相关
    └── message.py        # Pydantic模型：消息相关
```

## 技术栈

- **FastAPI**: Web服务和REST API
- **WebSocket**: 实时双向通信
- **LangGraph**: 多智能体框架
- **Pydantic**: 数据验证
- **AsyncIO**: 异步编程

## 后续迭代方向

- [ ] PostgreSQL持久化存储
- [ ] 用户认证和授权
- [ ] 评分系统
- [ ] 逻辑链可视化
- [ ] 案件模板系统
- [ ] 前端界面开发

## 许可证

MIT License
