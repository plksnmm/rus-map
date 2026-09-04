import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { PlaceMaterial } from '../api/places'
import PlaceMaterials from './PlaceMaterials'

const timestamp = '2026-09-04T09:00:00Z'

function material(
  overrides: Partial<PlaceMaterial> & Pick<PlaceMaterial, 'id' | 'type' | 'title'>,
): PlaceMaterial {
  return {
    source: null,
    revision: {
      revision_number: 1,
      content: null,
      url: 'https://example.com/material',
      created_at: timestamp,
    },
    created_at: timestamp,
    updated_at: timestamp,
    ...overrides,
  }
}

describe('PlaceMaterials', () => {
  it('shows text, source, image and safe external links', () => {
    const materials: PlaceMaterial[] = [
      material({
        id: 'text-id',
        type: 'text',
        title: 'История предприятия',
        source: 'Русь пролетарская',
        revision: {
          revision_number: 2,
          content: 'Архивный текст без HTML.',
          url: null,
          created_at: timestamp,
        },
      }),
      material({
        id: 'image-id',
        type: 'image',
        title: 'Фотография заводских корпусов',
        revision: {
          revision_number: 1,
          content: null,
          url: 'https://example.com/factory.jpg',
          created_at: timestamp,
        },
      }),
      material({
        id: 'video-id',
        type: 'video',
        title: 'Видеорепортаж',
      }),
      material({
        id: 'audio-id',
        type: 'audio',
        title: 'Воспоминания рабочего',
      }),
      material({
        id: 'link-id',
        type: 'external_link',
        title: 'Статья об истории',
      }),
    ]

    render(
      <PlaceMaterials materials={materials} isLoading={false} hasError={false} />,
    )

    expect(screen.getByText('Архивный текст без HTML.')).toBeInTheDocument()
    expect(screen.getByText('Источник: Русь пролетарская')).toBeInTheDocument()
    expect(
      screen.getByRole('img', { name: 'Фотография заводских корпусов' }),
    ).toHaveAttribute('loading', 'lazy')

    for (const link of screen.getAllByRole('link')) {
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noopener noreferrer')
      expect(link.getAttribute('href')).toMatch(/^https:\/\//)
    }

    expect(screen.getByRole('link', { name: /Смотреть видео/ })).toBeVisible()
    expect(screen.getByRole('link', { name: /Слушать аудио/ })).toBeVisible()
    expect(screen.getByRole('link', { name: /Открыть источник/ })).toBeVisible()
  })

  it('shows loading, error and empty states', () => {
    const { rerender } = render(
      <PlaceMaterials materials={[]} isLoading hasError={false} />,
    )
    expect(screen.getByRole('status')).toHaveTextContent('Загружаем материалы')

    rerender(<PlaceMaterials materials={[]} isLoading={false} hasError />)
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Основная информация о месте остаётся доступна',
    )

    rerender(
      <PlaceMaterials materials={[]} isLoading={false} hasError={false} />,
    )
    expect(screen.getByText('Материалы пока не добавлены.')).toBeInTheDocument()
  })
})
