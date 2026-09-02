import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import App from './App'

vi.mock('./components/MapView', () => ({
  default: () => (
    <div role="application" aria-label="Интерактивная карта" />
  ),
}))

describe('App', () => {
  it('renders the map foundation', async () => {
    render(<App />)

    expect(screen.getByText('Русь пролетарская')).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Исследуй историю вокруг' }),
    ).toBeInTheDocument()
    expect(
      await screen.findByRole('application', { name: 'Интерактивная карта' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Добавить место' }),
    ).toBeDisabled()
  })
})
