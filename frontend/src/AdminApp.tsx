import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  AdminApiError,
  fetchCurrentAdmin,
  fetchSubmissions,
  loginAdmin,
  logoutAdmin,
  moderateSubmission,
  type AdminUser,
  type PlaceSubmission,
  type SubmissionStatus,
} from './api/admin'
import { isSafeHttpUrl } from './api/places'
import './App.css'

type QueueFilter = SubmissionStatus | 'all'

const filters: { value: QueueFilter; label: string }[] = [
  { value: 'pending', label: 'Ожидают решения' },
  { value: 'approved', label: 'Одобрены' },
  { value: 'rejected', label: 'Отклонены' },
  { value: 'all', label: 'Все' },
]

const statusLabels: Record<SubmissionStatus, string> = {
  pending: 'На рассмотрении',
  approved: 'Одобрена',
  rejected: 'Отклонена',
}

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat('ru-RU', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function messageForError(error: unknown, fallback: string): string {
  if (error instanceof AdminApiError) {
    if (error.status === 401) {
      return 'Сессия завершилась. Войдите снова.'
    }
    if (error.status === 403) {
      return 'Защитный токен устарел. Обновите страницу и войдите снова.'
    }
    if (error.status === 409) {
      return 'Эту заявку уже обработали. Очередь обновлена.'
    }
    if (error.status === 429) {
      return 'Слишком много попыток входа. Попробуйте позднее.'
    }
  }
  return fallback
}

function AdminLogin({
  isBusy,
  error,
  onLogin,
}: {
  isBusy: boolean
  error: string | null
  onLogin: (username: string, password: string) => Promise<void>
}) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isPasswordVisible, setIsPasswordVisible] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await onLogin(username, password)
    setPassword('')
  }

  return (
    <section className="admin-login-card" aria-labelledby="admin-login-title">
      <div className="panel-kicker">Закрытый раздел</div>
      <h1 id="admin-login-title">Вход для редактора</h1>
      <p>
        Здесь проверяют предложенные места до их публикации на общей карте.
      </p>
      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit}>
        <label className="form-label" htmlFor="admin-username">
          Имя пользователя
        </label>
        <input
          id="admin-username"
          className="form-control"
          autoComplete="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          disabled={isBusy}
          required
        />
        <label className="form-label mt-3" htmlFor="admin-password">
          Пароль
        </label>
        <div className="admin-password-field">
          <input
            id="admin-password"
            className="form-control"
            type={isPasswordVisible ? 'text' : 'password'}
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={isBusy}
            required
          />
          <button
            className="admin-password-toggle"
            type="button"
            aria-label={isPasswordVisible ? 'Скрыть пароль' : 'Показать пароль'}
            aria-pressed={isPasswordVisible}
            onClick={() => setIsPasswordVisible((current) => !current)}
            disabled={isBusy}
          >
            <span aria-hidden="true">{isPasswordVisible ? '◉' : '◎'}</span>
          </button>
        </div>
        <button
          className="btn admin-primary-button mt-4 w-100"
          type="submit"
          disabled={isBusy}
        >
          {isBusy ? 'Входим…' : 'Войти'}
        </button>
      </form>
    </section>
  )
}

function SubmissionDetail({
  submission,
  isModerating,
  onDecision,
}: {
  submission: PlaceSubmission
  isModerating: boolean
  onDecision: (
    submission: PlaceSubmission,
    decision: 'approve' | 'reject',
    notes: string,
  ) => Promise<void>
}) {
  const [notes, setNotes] = useState(submission.review_notes ?? '')

  return (
    <article className="admin-submission-detail">
      <div className={`admin-status admin-status--${submission.status}`}>
        {statusLabels[submission.status]}
      </div>
      <h2>{submission.title}</h2>
      <div className="admin-detail-meta">
        <span>Получена {formatDate(submission.created_at)}</span>
        <span>
          {submission.latitude.toFixed(6)}, {submission.longitude.toFixed(6)}
        </span>
      </div>
      <section className="admin-detail-section">
        <h3>Описание</h3>
        <p>{submission.description || 'Описание не приложено.'}</p>
      </section>
      <section className="admin-detail-section">
        <h3>Источники</h3>
        {submission.source_urls.length > 0 ? (
          <ul className="admin-source-list">
            {submission.source_urls.map((url) => (
              <li key={url}>
                {isSafeHttpUrl(url) ? (
                  <a href={url} target="_blank" rel="noreferrer">
                    {url}
                  </a>
                ) : (
                  <span>{url}</span>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p>Ссылки на источники не приложены.</p>
        )}
      </section>
      {submission.status === 'pending' ? (
        <section className="admin-decision-section">
          <label className="form-label" htmlFor={`review-notes-${submission.id}`}>
            Примечание редактора
          </label>
          <textarea
            id={`review-notes-${submission.id}`}
            className="form-control"
            rows={4}
            maxLength={5000}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            disabled={isModerating}
            placeholder="Что проверено или почему заявка отклонена"
          />
          <div className="admin-decision-actions">
            <button
              className="btn admin-approve-button"
              type="button"
              disabled={isModerating}
              onClick={() => onDecision(submission, 'approve', notes)}
            >
              Одобрить и добавить на карту
            </button>
            <button
              className="btn admin-reject-button"
              type="button"
              disabled={isModerating}
              onClick={() => onDecision(submission, 'reject', notes)}
            >
              Отклонить
            </button>
          </div>
        </section>
      ) : (
        <section className="admin-detail-section">
          <h3>Результат проверки</h3>
          <p>{submission.review_notes || 'Примечание не оставлено.'}</p>
          {submission.moderated_at && (
            <small>Обработана {formatDate(submission.moderated_at)}</small>
          )}
        </section>
      )}
    </article>
  )
}

function AdminDashboard({
  admin,
  onSessionExpired,
  onLogout,
}: {
  admin: AdminUser
  onSessionExpired: (message: string) => void
  onLogout: () => Promise<void>
}) {
  const [filter, setFilter] = useState<QueueFilter>('pending')
  const [submissions, setSubmissions] = useState<PlaceSubmission[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isModerating, setIsModerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [reloadVersion, setReloadVersion] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    let isActive = true

    fetchSubmissions(filter === 'all' ? null : filter, controller.signal)
      .then((response) => {
        if (!isActive) {
          return
        }
        setSubmissions(response.items)
        setSelectedId((current) => {
          if (current && response.items.some((item) => item.id === current)) {
            return current
          }
          return response.items[0]?.id ?? null
        })
      })
      .catch((requestError: unknown) => {
        if (
          !isActive ||
          requestError instanceof DOMException &&
          requestError.name === 'AbortError'
        ) {
          return
        }
        if (requestError instanceof AdminApiError && requestError.status === 401) {
          onSessionExpired('Сессия завершилась. Войдите снова.')
          return
        }
        setError(messageForError(requestError, 'Не удалось загрузить очередь.'))
      })
      .finally(() => {
        if (isActive) {
          setIsLoading(false)
        }
      })

    return () => {
      isActive = false
      controller.abort()
    }
  }, [filter, onSessionExpired, reloadVersion])

  async function handleDecision(
    submission: PlaceSubmission,
    decision: 'approve' | 'reject',
    notes: string,
  ) {
    setIsModerating(true)
    setError(null)
    setNotice(null)
    try {
      await moderateSubmission(submission.id, decision, notes)
      setNotice(
        decision === 'approve'
          ? `«${submission.title}» добавлено на карту.`
          : `Заявка «${submission.title}» отклонена.`,
      )
      setIsLoading(true)
      setReloadVersion((current) => current + 1)
    } catch (requestError) {
      if (requestError instanceof AdminApiError && requestError.status === 401) {
        onSessionExpired('Сессия завершилась. Войдите снова.')
        return
      }
      setError(
        messageForError(requestError, 'Не удалось сохранить решение по заявке.'),
      )
      if (requestError instanceof AdminApiError && requestError.status === 409) {
        setIsLoading(true)
        setReloadVersion((current) => current + 1)
      }
    } finally {
      setIsModerating(false)
    }
  }

  const selected = submissions.find((item) => item.id === selectedId) ?? null

  return (
    <div className="admin-dashboard">
      <header className="admin-toolbar">
        <div>
          <div className="panel-kicker">Редакторская</div>
          <h1>Очередь предложенных мест</h1>
        </div>
        <div className="admin-account">
          <span>{admin.username}</span>
          <button className="btn btn-sm" type="button" onClick={onLogout}>
            Выйти
          </button>
        </div>
      </header>

      <nav className="admin-filters" aria-label="Статус заявок">
        {filters.map((item) => (
          <button
            key={item.value}
            className={filter === item.value ? 'is-active' : ''}
            type="button"
            aria-pressed={filter === item.value}
            onClick={() => {
              setIsLoading(true)
              setError(null)
              setFilter(item.value)
              setNotice(null)
            }}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {notice && (
        <div className="alert alert-success admin-message" role="status">
          {notice}
        </div>
      )}
      {error && (
        <div className="alert alert-danger admin-message" role="alert">
          {error}
          <button
            className="btn btn-sm ms-2"
            type="button"
            onClick={() => {
              setIsLoading(true)
              setError(null)
              setReloadVersion((current) => current + 1)
            }}
          >
            Повторить
          </button>
        </div>
      )}

      <div className="admin-workspace">
        <aside className="admin-queue" aria-label="Список заявок">
          {isLoading ? (
            <div className="admin-empty" role="status">
              Загружаем заявки…
            </div>
          ) : submissions.length === 0 ? (
            <div className="admin-empty" role="status">
              В этой очереди пока ничего нет.
            </div>
          ) : (
            submissions.map((submission) => (
              <button
                key={submission.id}
                className={`admin-queue-item${selectedId === submission.id ? ' is-active' : ''}`}
                type="button"
                onClick={() => setSelectedId(submission.id)}
              >
                <strong>{submission.title}</strong>
                <span>{formatDate(submission.created_at)}</span>
                <span className={`admin-status admin-status--${submission.status}`}>
                  {statusLabels[submission.status]}
                </span>
              </button>
            ))
          )}
        </aside>
        <main className="admin-detail-panel">
          {selected ? (
            <SubmissionDetail
              key={selected.id}
              submission={selected}
              isModerating={isModerating}
              onDecision={handleDecision}
            />
          ) : (
            <div className="admin-empty">Выберите заявку для проверки.</div>
          )}
        </main>
      </div>
    </div>
  )
}

function AdminApp() {
  const [admin, setAdmin] = useState<AdminUser | null>(null)
  const [isChecking, setIsChecking] = useState(true)
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [authError, setAuthError] = useState<string | null>(null)

  const expireSession = useCallback((message: string) => {
    setAdmin(null)
    setAuthError(message)
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    fetchCurrentAdmin(controller.signal)
      .then(setAdmin)
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') {
          return
        }
        if (!(error instanceof AdminApiError && error.status === 401)) {
          setAuthError('Не удалось проверить сессию администратора.')
        }
      })
      .finally(() => setIsChecking(false))
    return () => controller.abort()
  }, [])

  async function handleLogin(username: string, password: string) {
    setIsAuthenticating(true)
    setAuthError(null)
    try {
      const result = await loginAdmin(username, password)
      setAdmin(result.admin)
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 401) {
        setAuthError('Неверное имя пользователя или пароль.')
      } else {
        setAuthError(
          messageForError(error, 'Не удалось войти. Проверьте имя и пароль.'),
        )
      }
    } finally {
      setIsAuthenticating(false)
    }
  }

  async function handleLogout() {
    try {
      await logoutAdmin()
      setAuthError(null)
    } catch (error) {
      setAuthError(messageForError(error, 'Не удалось завершить сессию.'))
    } finally {
      setAdmin(null)
    }
  }

  return (
    <main className="admin-shell">
      <header className="navbar navbar-dark app-header admin-site-header px-3">
        <a className="brand-group text-decoration-none" href={import.meta.env.BASE_URL}>
          <span className="brand-mark" aria-hidden="true" />
          <div className="brand-copy">
            <span className="navbar-brand mb-0 h1">Русь пролетарская</span>
            <span className="app-subtitle d-none d-sm-block">
              Административный раздел
            </span>
          </div>
        </a>
        <a className="btn app-add-button btn-sm" href={import.meta.env.BASE_URL}>
          Вернуться к карте
        </a>
      </header>
      <div className="admin-content">
        {isChecking ? (
          <div className="admin-loading" role="status">
            Проверяем сессию…
          </div>
        ) : admin ? (
          <AdminDashboard
            admin={admin}
            onSessionExpired={expireSession}
            onLogout={handleLogout}
          />
        ) : (
          <AdminLogin
            isBusy={isAuthenticating}
            error={authError}
            onLogin={handleLogin}
          />
        )}
      </div>
    </main>
  )
}

export default AdminApp
