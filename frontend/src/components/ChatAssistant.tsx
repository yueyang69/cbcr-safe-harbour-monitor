import { useState, useRef, useEffect } from 'react'
import { chatAssistant } from '../api/endpoints'
import type { ChatMessage } from '../types'

export function ChatAssistant() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage: ChatMessage = { role: 'user', content: input.trim() }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await chatAssistant(userMessage.content)
      const assistantMessage: ChatMessage = { role: 'assistant', content: response.reply }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (err) {
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'AI助手暂时不可用，请稍后重试或联系您的税务顾问。',
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void sendMessage()
    }
  }

  return (
    <>
      {/* Floating button */}
      <button
        className="chat-assistant-button"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="税务助手"
        title="税务助手"
      >
        💬
      </button>

      {/* Chat window */}
      {isOpen && (
        <div className="chat-assistant-window">
          <div className="chat-assistant-header">
            <div>
              <h3>🤖 税务助手</h3>
              <p>仅解释已计算数值，不提供税务建议</p>
            </div>
            <button
              className="chat-close-button"
              onClick={() => setIsOpen(false)}
              aria-label="关闭"
            >
              ✕
            </button>
          </div>

          <div className="chat-assistant-messages">
            {messages.length === 0 && (
              <div className="chat-welcome">
                <p>您好！我可以帮您解释系统中已计算出的税务数据（如PBT、ETR、SBIE等）。</p>
                <p className="chat-disclaimer">
                  ⚠️ 注意：我无法提供补足税计算、避税方案或法律意见。如需专业建议，请联系您的税务顾问。
                </p>
              </div>
            )}

            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`chat-message chat-message-${msg.role}`}
              >
                <div className="chat-message-avatar">
                  {msg.role === 'user' ? '👤' : '🤖'}
                </div>
                <div className="chat-message-content">{msg.content}</div>
              </div>
            ))}

            {loading && (
              <div className="chat-message chat-message-assistant">
                <div className="chat-message-avatar">🤖</div>
                <div className="chat-message-content chat-loading">
                  正在思考...
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <div className="chat-assistant-input">
            <input
              type="text"
              placeholder="输入您的问题..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={loading}
            />
            <button
              onClick={() => void sendMessage()}
              disabled={!input.trim() || loading}
              className="chat-send-button"
            >
              发送
            </button>
          </div>
        </div>
      )}
    </>
  )
}
