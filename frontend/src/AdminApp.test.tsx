import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AdminApp from './AdminApp'
import {
  AdminApiError,
  fetchCurrentAdmin,
  fetchSubmissions,
  loginAdmin,
  logoutAdmin,
  moderateSubmission,
  type PlaceSubmission,
} from './api/admin'

vi.mock('./api/admin', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api/admin')>()
  return {
    ...actual,
    fetchCurrentAdmin: vi.fn(),
    fetchSubmissions: vi.fn(),
    loginAdmin: vi.fn(),
    logoutAdmin: vi.fn(),
    moderateSubmission: vi.fn(),
  }
})

const fetchCurrentAdminMock = vi.mocked(fetchCurrentAdmin)
const fetchSubmissionsMock = vi.mocked(fetchSubmissions)
const loginAdminMock = vi.mocked(loginAdmin)
const logoutAdminMock = vi.mocked(logoutAdmin)
const moderateSubmissionMock = vi.mocked(moderateSubmission)

const admin = { id: 'admin-id', username: 'editor' }

function pendingSubmission(): PlaceSubmission {
  return {
    id: '11111111-1111-4111-8111-111111111111',
    status: 'pending',
    title: 'Опытный завод',
    description: 'Историческое промышленное предприятие.',
    latitude: 55.7,
    longitude: 37.6,
    source_urls: ['https://example.com/archive'],
    review_notes: null,
    approved_place_id: null,
    moderated_by_admin_id: null,
    moderated_at: null,
    created_at: '2026-09-10T10:00:00Z',
    updated_at: '2026-09-10T10:00:00Z',
  }
}

describe('AdminApp', () => {
  beforeEach(() => {
    fetchCurrentAdminMock.mockReset()
    fetchSubmissionsMock.mockReset()
    loginAdminMock.mockReset()
    logoutAdminMock.mockReset()
    moderateSubmissionMock.mockReset()
    fetchSubmissionsMock.mockResolvedValue({
      items: [],
      total: 0,
      limit: 100,
      offset: 0,
    })
  })

  it('shows the login form when there is no active session', async () => {
    fetchCurrentAdminMock.mockRejectedValue(new AdminApiError(401, 'HTTP 401'))

    render(<AdminApp />)

    expect(
      await screen.findByRole('heading', { name: 'Вход для редактора' }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Пароль')).toHaveAttribute('type', 'password')

    fireEvent.click(screen.getByRole('button', { name: 'Показать пароль' }))
    expect(screen.getByLabelText('Пароль')).toHaveAttribute('type', 'text')
    fireEvent.click(screen.getByRole('button', { name: 'Скрыть пароль' }))
    expect(screen.getByLabelText('Пароль')).toHaveAttribute('type', 'password')
  })

  it('logs in and loads the pending queue', async () => {
    fetchCurrentAdminMock.mockRejectedValue(new AdminApiError(401, 'HTTP 401'))
    loginAdminMock.mockResolvedValue({
      admin,
      expires_at: '2026-09-11T10:00:00Z',
    })

    render(<AdminApp />)
    fireEvent.change(await screen.findByLabelText('Имя пользователя'), {
      target: { value: 'editor' },
    })
    fireEvent.change(screen.getByLabelText('Пароль'), {
      target: { value: 'secret password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Войти' }))

    expect(
      await screen.findByRole('heading', { name: 'Очередь предложенных мест' }),
    ).toBeInTheDocument()
    expect(loginAdminMock).toHaveBeenCalledWith('editor', 'secret password')
    expect(fetchSubmissionsMock).toHaveBeenCalledWith(
      'pending',
      expect.any(AbortSignal),
    )
  })

  it('shows a submission and approves it with review notes', async () => {
    const submission = pendingSubmission()
    fetchCurrentAdminMock.mockResolvedValue(admin)
    fetchSubmissionsMock
      .mockResolvedValueOnce({
        items: [submission],
        total: 1,
        limit: 100,
        offset: 0,
      })
      .mockResolvedValue({ items: [], total: 0, limit: 100, offset: 0 })
    moderateSubmissionMock.mockResolvedValue({
      ...submission,
      status: 'approved',
      approved_place_id: 'place-id',
      moderated_by_admin_id: admin.id,
      moderated_at: '2026-09-10T12:00:00Z',
    })

    render(<AdminApp />)

    expect(
      await screen.findByRole('heading', { name: submission.title }),
    ).toBeInTheDocument()
    expect(screen.getByText(submission.description!)).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: submission.source_urls[0] }),
    ).toHaveAttribute('target', '_blank')
    fireEvent.change(screen.getByLabelText('Примечание редактора'), {
      target: { value: 'Источники проверены' },
    })
    fireEvent.click(
      screen.getByRole('button', { name: 'Одобрить и добавить на карту' }),
    )

    await waitFor(() =>
      expect(moderateSubmissionMock).toHaveBeenCalledWith(
        submission.id,
        'approve',
        'Источники проверены',
      ),
    )
    expect(
      await screen.findByText(`«${submission.title}» добавлено на карту.`),
    ).toBeInTheDocument()
  })

  it('logs out and returns to the login form', async () => {
    fetchCurrentAdminMock.mockResolvedValue(admin)
    logoutAdminMock.mockResolvedValue()

    render(<AdminApp />)
    fireEvent.click(await screen.findByRole('button', { name: 'Выйти' }))

    expect(
      await screen.findByRole('heading', { name: 'Вход для редактора' }),
    ).toBeInTheDocument()
    expect(logoutAdminMock).toHaveBeenCalledOnce()
  })
})
