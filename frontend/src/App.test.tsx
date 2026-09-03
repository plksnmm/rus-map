import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { fetchPlaces } from './api/places'

vi.mock('./api/places', () => ({
  fetchPlaces: vi.fn(),
}))

vi.mock('./components/MapView', () => ({
  default: ({ places }: { places: unknown[] }) => (
    <div
      role="application"
      aria-label="Интерактивная карта"
      data-place-count={places.length}
    />
  ),
}))

const fetchPlacesMock = vi.mocked(fetchPlaces)

describe('App', () => {
  beforeEach(() => {
    fetchPlacesMock.mockReset()
    fetchPlacesMock.mockResolvedValue({ items: [], total: 0 })
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
})
