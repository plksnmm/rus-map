import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  AdminApiError,
  fetchCurrentAdmin,
  fetchSubmissions,
  loginAdmin,
  logoutAdmin,
  moderateSubmission,
  readCsrfToken,
} from './admin'

const submission = {
  id: '11111111-1111-4111-8111-111111111111',
  status: 'pending',
  title: 'Завод',
  description: 'Описание',
  latitude: 55.7,
  longitude: 37.6,
  source_urls: ['https://example.com/source'],
  review_notes: null,
  approved_place_id: null,
  moderated_by_admin_id: null,
  moderated_at: null,
  created_at: '2026-09-10T10:00:00Z',
  updated_at: '2026-09-10T10:00:00Z',
}

describe('admin API', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    Object.defineProperty(document, 'cookie', {
      configurable: true,
      value: '',
    })
  })

  it('reads and decodes only the CSRF cookie', () => {
    expect(readCsrfToken('other=value; rus_map_admin_csrf=secret%20token')).toBe(
      'secret token',
    )
    expect(readCsrfToken('other=value')).toBeNull()
  })

  it('logs in without exposing tokens in the response contract', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          admin: { id: 'admin-id', username: 'editor' },
          expires_at: '2026-09-11T10:00:00Z',
        }),
        { status: 200 },
      ),
    )

    await expect(loginAdmin('editor', 'long password')).resolves.toMatchObject({
      admin: { username: 'editor' },
    })
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/admin/auth/login'),
      expect.objectContaining({ credentials: 'same-origin', method: 'POST' }),
    )
  })

  it('loads the current administrator and filtered queue', async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: 'admin-id', username: 'editor' })),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ items: [submission], total: 1, limit: 100, offset: 0 }),
        ),
      )

    await expect(fetchCurrentAdmin()).resolves.toMatchObject({ username: 'editor' })
    await expect(fetchSubmissions('pending')).resolves.toMatchObject({ total: 1 })
    expect(vi.mocked(fetch).mock.calls[1][0]).toContain('status=pending')
  })

  it('sends CSRF with moderation and logout requests', async () => {
    Object.defineProperty(document, 'cookie', {
      configurable: true,
      value: 'rus_map_admin_csrf=csrf-secret',
    })
    vi.mocked(fetch)
      .mockResolvedValueOnce(new Response(JSON.stringify(submission)))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))

    await moderateSubmission(submission.id, 'approve', 'Проверено')
    await logoutAdmin()

    for (const call of vi.mocked(fetch).mock.calls) {
      expect(call[1]).toEqual(
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({ 'X-CSRF-Token': 'csrf-secret' }),
        }),
      )
    }
  })

  it('reports HTTP status and refuses mutation without CSRF', async () => {
    Object.defineProperty(document, 'cookie', {
      configurable: true,
      value: '',
    })
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 401 }))

    await expect(fetchCurrentAdmin()).rejects.toMatchObject({ status: 401 })
    await expect(
      moderateSubmission(submission.id, 'reject', ''),
    ).rejects.toBeInstanceOf(AdminApiError)
    expect(fetch).toHaveBeenCalledTimes(1)
  })

})
