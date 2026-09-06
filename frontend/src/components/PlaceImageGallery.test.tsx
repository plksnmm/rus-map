import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { PlaceMaterial } from '../api/places'
import PlaceImageGallery from './PlaceImageGallery'

const timestamp = '2026-09-05T10:00:00Z'

function image(id: string, title: string): PlaceMaterial {
  return {
    id,
    type: 'image',
    title,
    source: 'Государственный каталог',
    revision: {
      revision_number: 1,
      content: null,
      url: `https://example.com/catalog/${id}`,
      media_id: `media-${id}`,
      created_at: timestamp,
    },
    created_at: timestamp,
    updated_at: timestamp,
  }
}

const images = [
  image('one', 'Опытный цех, 1964 год'),
  image('two', 'Пульт установки, 1964 год'),
  image('three', 'Машина для литья образцов, 1964 год'),
]

describe('PlaceImageGallery', () => {
  it('renders nothing without images', () => {
    const { container } = render(
      <PlaceImageGallery placeId="place-id" images={[]} />,
    )

    expect(container).toBeEmptyDOMElement()
  })

  it('shows one image with its caption and source without navigation', () => {
    render(<PlaceImageGallery placeId="place-id" images={[images[0]]} />)

    expect(
      screen.getByRole('img', { name: 'Опытный цех, 1964 год' }),
    ).toHaveAttribute('src', '/api/v1/places/place-id/images/media-one')
    expect(screen.getByText('1 / 1')).toBeInTheDocument()
    expect(screen.getByText('Государственный каталог')).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /Открыть источник/ }),
    ).toHaveAttribute('href', 'https://example.com/catalog/one')
    expect(
      screen.queryByRole('button', { name: 'Следующая фотография' }),
    ).not.toBeInTheDocument()
  })

  it('switches images with arrows, thumbnails and keyboard', () => {
    render(<PlaceImageGallery placeId="place-id" images={images} />)

    fireEvent.click(
      screen.getByRole('button', { name: 'Следующая фотография' }),
    )
    expect(screen.getByText('2 / 3')).toBeInTheDocument()
    expect(
      screen.getByRole('img', { name: 'Пульт установки, 1964 год' }),
    ).toBeInTheDocument()

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Показать фотографию 3: Машина для литья образцов, 1964 год',
      }),
    )
    expect(screen.getByText('3 / 3')).toBeInTheDocument()

    fireEvent.keyDown(screen.getByRole('region', { name: 'Фотографии' }), {
      key: 'ArrowRight',
    })
    expect(screen.getByText('1 / 3')).toBeInTheDocument()

    fireEvent.click(
      screen.getByRole('button', { name: 'Предыдущая фотография' }),
    )
    expect(screen.getByText('3 / 3')).toBeInTheDocument()
  })

  it('opens the active image and closes the lightbox with Escape', () => {
    render(<PlaceImageGallery placeId="place-id" images={images} />)

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Открыть фотографию крупно: Опытный цех, 1964 год',
      }),
    )
    expect(
      screen.getByRole('dialog', {
        name: 'Просмотр фотографии: Опытный цех, 1964 год',
      }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Закрыть просмотр фотографии' }),
    ).toHaveFocus()

    fireEvent.keyDown(window, { key: 'ArrowRight' })
    expect(
      screen.getByRole('dialog', {
        name: 'Просмотр фотографии: Пульт установки, 1964 год',
      }),
    ).toBeInTheDocument()

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(
      screen.getByRole('button', {
        name: 'Открыть фотографию крупно: Пульт установки, 1964 год',
      }),
    ).toHaveFocus()
  })
})
