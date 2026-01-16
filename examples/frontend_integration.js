// 数字法庭前端集成示例
// 这个示例展示了如何使用原生JavaScript与后端API交互

class DigitalCourtroomClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.ws = null;
        this.sessionId = null;
    }

    // 创建新的法庭会话
    async createSession(caseInfo, caseEvidence = [], humanRole = null) {
        try {
            const response = await fetch(`${this.baseUrl}/api/sessions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    case_info: caseInfo,
                    case_evidence: caseEvidence,
                    human_role: humanRole
                })
            });

            if (!response.ok) {
                throw new Error(`创建会话失败: ${response.status}`);
            }

            const data = await response.json();
            this.sessionId = data.session_id;
            console.log('会话创建成功:', data);
            return data;
        } catch (error) {
            console.error('创建会话出错:', error);
            throw error;
        }
    }

    // 获取会话状态
    async getSessionStatus() {
        if (!this.sessionId) {
            throw new Error('请先创建会话');
        }

        try {
            const response = await fetch(`${this.baseUrl}/api/sessions/${this.sessionId}`);

            if (!response.ok) {
                throw new Error(`获取状态失败: ${response.status}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('获取状态出错:', error);
            throw error;
        }
    }

    // 连接WebSocket
    connectWebSocket(role = null, callbacks = {}) {
        if (!this.sessionId) {
            throw new Error('请先创建会话');
        }

        const wsUrl = `ws://${this.baseUrl.replace('http://', '')}/ws/${this.sessionId}`;
        const url = role ? `${wsUrl}?role=${role}` : wsUrl;

        this.ws = new WebSocket(url);

        // WebSocket事件处理
        this.ws.onopen = () => {
            console.log('WebSocket连接已建立');
            if (callbacks.onOpen) callbacks.onOpen();
        };

        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            console.log('收到消息:', message);

            switch (message.event) {
                case 'connected':
                    if (callbacks.onConnected) callbacks.onConnected(message.data);
                    break;

                case 'status_update':
                    if (callbacks.onStatusUpdate) callbacks.onStatusUpdate(message.data);
                    break;

                case 'debate_update':
                    if (callbacks.onDebateUpdate) callbacks.onDebateUpdate(message.data);
                    break;

                case 'human_input_required':
                    if (callbacks.onHumanInputRequired) {
                        callbacks.onHumanInputRequired(message.data);
                    }
                    break;

                case 'debate_ended':
                    if (callbacks.onDebateEnded) callbacks.onDebateEnded(message.data);
                    break;

                case 'error':
                    if (callbacks.onError) callbacks.onError(message.data);
                    break;
            }
        };

        this.ws.onclose = () => {
            console.log('WebSocket连接已关闭');
            if (callbacks.onClose) callbacks.onClose();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket错误:', error);
            if (callbacks.onError) callbacks.onError(error);
        };

        return this.ws;
    }

    // 发送人类输入
    sendHumanInput(content, role) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            throw new Error('WebSocket未连接');
        }

        const message = {
            event: 'human_input',
            data: {
                content: content,
                role: role
            }
        };

        this.ws.send(JSON.stringify(message));
        console.log('发送人类输入:', message);
    }

    // 请求下一步（AI模式）
    requestNextStep() {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            throw new Error('WebSocket未连接');
        }

        const message = {
            event: 'next_step',
            data: {}
        };

        this.ws.send(JSON.stringify(message));
        console.log('请求下一步');
    }

    // 关闭WebSocket连接
    closeWebSocket() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    // 结束会话
    async endSession() {
        if (!this.sessionId) {
            throw new Error('没有活跃的会话');
        }

        try {
            const response = await fetch(`${this.baseUrl}/api/sessions/${this.sessionId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error(`结束会话失败: ${response.status}`);
            }

            const data = await response.json();
            console.log('会话已结束:', data);

            this.closeWebSocket();
            this.sessionId = null;

            return data;
        } catch (error) {
            console.error('结束会话出错:', error);
            throw error;
        }
    }
}

// 使用示例
// ========

async function runDemo() {
    // 创建客户端实例
    const client = new DigitalCourtroomClient('http://localhost:8000');

    // 定义回调函数
    const callbacks = {
        onConnected: (data) => {
            console.log('连接成功:', data);
        },

        onDebateUpdate: (data) => {
            if (data.new_message) {
                const msg = data.new_message;
                console.log(`${msg.sender}: ${msg.content}`);

                // 在页面上显示消息
                displayMessage(msg.sender, msg.content);
            }
        },

        onHumanInputRequired: (data) => {
            console.log('需要输入:', data.prompt);
            alert(`需要${data.required_role}输入:\n${data.prompt}`);

            // 显示输入框
            showInputDialog(data.required_role, data.prompt);
        },

        onDebateEnded: (data) => {
            console.log('辩论结束:', data);
            alert('法庭辩论已结束！');
        },

        onError: (error) => {
            console.error('错误:', error);
            alert(`错误: ${error.message || error}`);
        }
    };

    try {
        // 1. 创建会话
        const session = await client.createSession(
            '张三于2023年1月向李四借款10万元，约定3个月归还，但至今未还。',
            [
                {
                    speaker: '原告律师',
                    content: '借条照片：显示张三于2023年1月15日借款10万元，约定2023年4月15日归还'
                }
            ],
            '被告律师'  // 人类扮演被告律师，null表示纯AI模式
        );

        // 2. 连接WebSocket
        client.connectWebSocket('被告律师', callbacks);

        // 3. 等待辩论进行...
        // 系统会自动推进，当需要人类输入时会触发onHumanInputRequired回调

    } catch (error) {
        console.error('Demo failed:', error);
    }
}

// 页面显示函数（需要根据实际页面结构实现）
function displayMessage(sender, content) {
    const messageList = document.getElementById('message-list');
    if (messageList) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message';
        messageDiv.innerHTML = `
            <strong>${sender}:</strong>
            <p>${content}</p>
        `;
        messageList.appendChild(messageDiv);
        messageList.scrollTop = messageList.scrollHeight;
    }
}

function showInputDialog(role, prompt) {
    const input = prompt(`[${role}] ${prompt}`);
    if (input) {
        // 发送人类输入
        client.sendHumanInput(input, role);
    }
}

// 在页面加载完成后运行Demo
// window.addEventListener('load', runDemo);
