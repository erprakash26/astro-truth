import { useEffect, useState } from 'react'
import { getConfig, chatWithChart } from '../api'
import { t } from '../i18n'

export default function ChatPanel({ lang, shareId }) {
  const [mockLlm, setMockLlm] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    getConfig()
      .then((cfg) => setMockLlm(cfg.mock_llm))
      .catch(() => setMockLlm(null))
  }, [])

  async function handleSend(e) {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || sending) return

    setSending(true)
    setError(null)
    const history = messages
    const nextMessages = [...messages, { role: 'user', content: trimmed }]
    setMessages(nextMessages)
    setInput('')

    try {
      const { reply } = await chatWithChart({ shareId, message: trimmed, history })
      setMessages([...nextMessages, { role: 'assistant', content: reply }])
    } catch (err) {
      setError(err.message || t(lang, 'chatError'))
    } finally {
      setSending(false)
    }
  }

  const placeholder = mockLlm ? t(lang, 'chatPlaceholderMock') : t(lang, 'chatPlaceholder')

  return (
    <div className="rounded-xl border border-gold-500/30 bg-cream-50 p-5">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="font-serif text-xl font-semibold text-maroon-700">{t(lang, 'chatTitle')}</h2>
        {mockLlm && (
          <span
            className="rounded-full bg-gold-400/30 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-maroon-600"
            data-testid="chat-mock-badge"
          >
            {t(lang, 'mockBadge')}
          </span>
        )}
      </div>

      {mockLlm && (
        <p className="mb-3 text-xs text-maroon-500" data-testid="chat-mock-note">
          {t(lang, 'chatMockNote')}
        </p>
      )}

      {messages.length > 0 && (
        <div className="mb-3 max-h-72 space-y-2 overflow-y-auto" data-testid="chat-messages">
          {messages.map((m, i) => (
            <div
              key={i}
              className={
                m.role === 'user'
                  ? 'ml-8 rounded-lg bg-gold-400/20 p-3 text-sm text-maroon-700'
                  : 'mr-8 rounded-lg bg-cream-100 p-3 text-sm text-maroon-600'
              }
              data-testid={`chat-message-${m.role}`}
            >
              {m.content}
            </div>
          ))}
        </div>
      )}

      {error && (
        <p className="mb-2 text-sm font-medium text-maroon-500" data-testid="chat-error">
          {error}
        </p>
      )}

      <form onSubmit={handleSend} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          className="flex-1 rounded-md border border-maroon-100 bg-cream-50 px-3 py-2 text-sm text-maroon-700 focus:border-gold-500 focus:outline-none focus:ring-2 focus:ring-gold-400/40"
          data-testid="chat-input"
        />
        <button
          type="submit"
          disabled={sending}
          className="rounded-md bg-maroon-500 px-4 py-2 text-sm font-semibold text-gold-300 shadow-md hover:bg-maroon-600 disabled:cursor-not-allowed disabled:opacity-60"
          data-testid="chat-send-button"
        >
          {sending ? t(lang, 'chatSending') : t(lang, 'chatSend')}
        </button>
      </form>
    </div>
  )
}
