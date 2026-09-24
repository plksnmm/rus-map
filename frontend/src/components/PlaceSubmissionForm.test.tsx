import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { searchAddress } from '../api/geocoding'
import { submitPlace } from '../api/submissions'
import PlaceSubmissionForm from './PlaceSubmissionForm'

vi.mock('../api/submissions', () => ({ submitPlace: vi.fn() }))
vi.mock('../api/geocoding', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/geocoding')>()
  return { ...actual, searchAddress: vi.fn() }
})

const submitPlaceMock = vi.mocked(submitPlace)
const searchAddressMock = vi.mocked(searchAddress)

describe('PlaceSubmissionForm', () => {
  beforeEach(() => {
    submitPlaceMock.mockReset()
    searchAddressMock.mockReset()
    searchAddressMock.mockResolvedValue({
      items: [],
      attribution: '© OpenStreetMap contributors',
      attribution_url: 'https://www.openstreetmap.org/copyright',
    })
    submitPlaceMock.mockResolvedValue({
      id: 'ea261f5b-5420-4500-879d-400d6ea82a79',
      status: 'pending',
      created_at: '2026-09-13T10:00:00Z',
    })
  })

  it('requires a map location before submission', () => {
    render(
      <PlaceSubmissionForm
        location={null}
        onCancel={vi.fn()}
        onLocationCleared={vi.fn()}
        onLocationFound={vi.fn()}
        onSubmitted={vi.fn()}
      />,
    )

    fireEvent.change(screen.getByLabelText(/Название места/), {
      target: { value: 'Старый завод' },
    })
    expect(
      screen.getByRole('button', { name: 'Отправить на проверку' }),
    ).toBeDisabled()
    expect(screen.getByText('Или нажмите на нужное место на карте')).toBeInTheDocument()
  })

  it('finds an address and passes its location to the map', async () => {
    const onLocationFound = vi.fn()
    const result = {
      display_name:
        'Нижний Новгород, Нижегородская область, Приволжский федеральный округ, Россия',
      latitude: 56.3269,
      longitude: 44.0059,
      bounding_box: [56.18, 56.41, 43.72, 44.13] as [
        number,
        number,
        number,
        number,
      ],
    }
    searchAddressMock.mockResolvedValue({
      items: [result],
      attribution: '© OpenStreetMap contributors',
      attribution_url: 'https://www.openstreetmap.org/copyright',
    })
    render(
      <PlaceSubmissionForm
        location={null}
        onCancel={vi.fn()}
        onLocationCleared={vi.fn()}
        onLocationFound={onLocationFound}
        onSubmitted={vi.fn()}
      />,
    )

    fireEvent.change(screen.getByLabelText('Адрес или название места'), {
      target: { value: 'Нижний Новгород' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Найти' }))
    expect(
      screen.queryByText(/Ничего не найдено/),
    ).not.toBeInTheDocument()
    fireEvent.click(await screen.findByRole('button', { name: result.display_name }))

    expect(searchAddressMock).toHaveBeenCalledWith('Нижний Новгород')
    expect(onLocationFound).toHaveBeenCalledWith(result)
    expect(screen.getByLabelText('Адрес или название места')).toHaveValue(
      'Нижний Новгород',
    )
    expect(screen.getByRole('status')).toHaveTextContent(
      `Выбрано: ${result.display_name}`,
    )
  })

  it('sends trimmed content and one source URL per line', async () => {
    const onSubmitted = vi.fn()
    render(
      <PlaceSubmissionForm
        location={{ latitude: 56.494711, longitude: 60.809612 }}
        onCancel={vi.fn()}
        onLocationCleared={vi.fn()}
        onLocationFound={vi.fn()}
        onSubmitted={onSubmitted}
      />,
    )

    fireEvent.change(screen.getByLabelText(/Название места/), {
      target: { value: '  Сысертский завод  ' },
    })
    fireEvent.change(screen.getByLabelText(/Что здесь/), {
      target: { value: '  История завода  ' },
    })
    fireEvent.change(screen.getByLabelText('Адрес или название места'), {
      target: { value: '  Сысерть, улица Тимирязева, 1  ' },
    })
    fireEvent.change(screen.getByLabelText(/Ссылки на источники/), {
      target: { value: 'https://example.com/one\n\nhttps://example.com/two' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Отправить на проверку' }))

    await waitFor(() => expect(onSubmitted).toHaveBeenCalledOnce())
    expect(submitPlaceMock).toHaveBeenCalledWith({
      title: 'Сысертский завод',
      description: 'История завода',
      latitude: 56.494711,
      longitude: 60.809612,
      address: 'Сысерть, улица Тимирязева, 1',
      source_urls: ['https://example.com/one', 'https://example.com/two'],
      website: '',
    })
  })

  it('clears stale coordinates when the address changes', () => {
    const onLocationCleared = vi.fn()
    render(
      <PlaceSubmissionForm
        location={{ latitude: 43.200203, longitude: 40.566317 }}
        onCancel={vi.fn()}
        onLocationCleared={onLocationCleared}
        onLocationFound={vi.fn()}
        onSubmitted={vi.fn()}
      />,
    )

    fireEvent.change(screen.getByLabelText('Адрес или название места'), {
      target: { value: 'Санкт-Петербург, Московское шоссе, 13АЕ' },
    })

    expect(onLocationCleared).toHaveBeenCalledOnce()
  })
})
