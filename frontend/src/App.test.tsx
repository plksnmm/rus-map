import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { fetchPlace, fetchPlaceMaterials, fetchPlaces } from './api/places'

vi.mock('./api/places', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api/places')>()

  return {
    ...actual,
    fetchPlace: vi.fn(),
    fetchPlaceMaterials: vi.fn(),
    fetchPlaces: vi.fn(),
  }
})

vi.mock('./components/MapView', () => ({
  default: ({
    places,
    onSelectPlace,
  }: {
    places: { id: string }[]
    onSelectPlace: (placeId: string) => void
  }) => (
    <>
      <div
        role="application"
        aria-label="Интерактивная карта"
        data-place-count={places.length}
      />
      {places[0] && (
        <button type="button" onClick={() => onSelectPlace(places[0].id)}>
          Выбрать место на карте
        </button>
      )}
    </>
  ),
}))

vi.mock('./AdminApp', () => ({
  default: () => <div>Тестовая панель администратора</div>,
}))

const fetchPlacesMock = vi.mocked(fetchPlaces)
const fetchPlaceMock = vi.mocked(fetchPlace)
const fetchPlaceMaterialsMock = vi.mocked(fetchPlaceMaterials)

describe('App', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/')
    fetchPlacesMock.mockReset()
    fetchPlaceMock.mockReset()
    fetchPlaceMaterialsMock.mockReset()
    fetchPlacesMock.mockResolvedValue({ items: [], total: 0 })
    fetchPlaceMaterialsMock.mockResolvedValue({ items: [], total: 0 })
  })

  it('opens the administrator interface on its own SPA path', () => {
    window.history.replaceState({}, '', '/admin')

    render(<App />)

    expect(screen.getByText('Тестовая панель администратора')).toBeInTheDocument()
    expect(fetchPlacesMock).not.toHaveBeenCalled()
  })

  it('renders the map foundation', async () => {
    render(<App />)

    expect(screen.getByText('Русь пролетарская')).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Исследуй историю вокруг' }),
    ).toBeInTheDocument()
    expect(
      await screen.findByRole('application', { name: 'Интерактивная карта' }),
    ).toBeInTheDocument()
    expect(await screen.findByText('На карте пока нет мест.')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Добавить место' }),
    ).toBeDisabled()
    expect(screen.getByRole('link', { name: 'Редакторская' })).toHaveAttribute(
      'href',
      '/admin',
    )
  })

  it('shows loading while the API request is pending', () => {
    fetchPlacesMock.mockReturnValue(new Promise(() => undefined))

    render(<App />)

    expect(screen.getByText('Загружаем места…')).toBeInTheDocument()
    expect(
      screen.getByRole('application', { name: 'Интерактивная карта' }),
    ).toBeInTheDocument()
  })

  it('passes loaded places to the map', async () => {
    fetchPlacesMock.mockResolvedValue({
      items: [
        {
          id: 'db21fe63-a06c-49de-8762-70cbe9c51601',
          title: 'Завод «Красный богатырь»',
          latitude: 55.811,
          longitude: 37.691,
        },
      ],
      total: 1,
    })

    render(<App />)

    expect(await screen.findByText('На карте мест:')).toHaveTextContent(
      'На карте мест: 1',
    )
    expect(
      screen.getByRole('application', { name: 'Интерактивная карта' }),
    ).toHaveAttribute('data-place-count', '1')
  })

  it('keeps the map available when the API request fails', async () => {
    fetchPlacesMock.mockRejectedValue(new Error('Network error'))

    render(<App />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Не удалось загрузить места',
    )
    expect(
      screen.getByRole('application', { name: 'Интерактивная карта' }),
    ).toBeInTheDocument()
  })

  it('shows complete place details after a marker is selected', async () => {
    const place = {
      id: 'e2457cad-b0e2-45b4-8e76-81e09b3d1fed',
      title: 'Сысертский электротехнический завод',
      latitude: 56.494711,
      longitude: 60.809612,
    }
    fetchPlacesMock.mockResolvedValue({ items: [place], total: 1 })
    fetchPlaceMock.mockResolvedValue({
      ...place,
      description: 'Советское предприятие в исторических корпусах.',
      created_at: '2026-09-03T20:22:56.888798Z',
      updated_at: '2026-09-03T20:29:00Z',
    })
    fetchPlaceMaterialsMock.mockResolvedValue({
      items: [
        {
          id: 'image-id',
          type: 'image',
          title: 'Архивный заводской цех',
          source: 'Государственный каталог',
          revision: {
            revision_number: 1,
            content: null,
            url: 'https://example.com/archive-image',
            media_id: 'media-id',
            created_at: '2026-09-03T20:22:56.888798Z',
          },
          created_at: '2026-09-03T20:22:56.888798Z',
          updated_at: '2026-09-03T20:22:56.888798Z',
        },
      ],
      total: 1,
    })

    render(<App />)
    fireEvent.click(await screen.findByText('Выбрать место на карте'))

    expect(
      await screen.findByRole('heading', { name: place.title }),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Советское предприятие в исторических корпусах.'),
    ).toBeInTheDocument()
    const gallery = await screen.findByRole('region', { name: 'Фотографии' })
    const description = screen.getByText(
      'Советское предприятие в исторических корпусах.',
    )
    expect(
      gallery.compareDocumentPosition(description) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(fetchPlaceMock).toHaveBeenCalledWith(place.id, expect.any(AbortSignal))
    expect(fetchPlaceMaterialsMock).toHaveBeenCalledWith(
      place.id,
      expect.any(AbortSignal),
    )
    expect(
      screen.queryByText('Материалы пока не добавлены.'),
    ).not.toBeInTheDocument()

    fireEvent.click(
      screen.getByRole('button', { name: 'Закрыть карточку места' }),
    )
    expect(
      screen.getByRole('heading', { name: 'Исследуй историю вокруг' }),
    ).toBeInTheDocument()
  })

  it('keeps the map available when place details fail to load', async () => {
    const place = {
      id: 'e2457cad-b0e2-45b4-8e76-81e09b3d1fed',
      title: 'Сысертский электротехнический завод',
      latitude: 56.494711,
      longitude: 60.809612,
    }
    fetchPlacesMock.mockResolvedValue({ items: [place], total: 1 })
    fetchPlaceMock.mockRejectedValue(new Error('Network error'))

    render(<App />)
    fireEvent.click(await screen.findByText('Выбрать место на карте'))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Не удалось загрузить информацию о месте',
    )
    expect(
      screen.getByRole('application', { name: 'Интерактивная карта' }),
    ).toBeInTheDocument()
  })

  it('keeps place details available when materials fail to load', async () => {
    const place = {
      id: 'e2457cad-b0e2-45b4-8e76-81e09b3d1fed',
      title: 'Сысертский электротехнический завод',
      latitude: 56.494711,
      longitude: 60.809612,
    }
    fetchPlacesMock.mockResolvedValue({ items: [place], total: 1 })
    fetchPlaceMock.mockResolvedValue({
      ...place,
      description: 'Описание завода остаётся доступным.',
      created_at: '2026-09-03T20:22:56.888798Z',
      updated_at: '2026-09-03T20:29:00Z',
    })
    fetchPlaceMaterialsMock.mockRejectedValue(new Error('Network error'))

    render(<App />)
    fireEvent.click(await screen.findByText('Выбрать место на карте'))

    expect(
      await screen.findByText('Описание завода остаётся доступным.'),
    ).toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Не удалось загрузить материалы',
    )
    expect(
      screen.getByRole('application', { name: 'Интерактивная карта' }),
    ).toBeInTheDocument()
  })
})
