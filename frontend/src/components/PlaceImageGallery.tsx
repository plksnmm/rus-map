import { useEffect, useRef, useState } from 'react'
import { isSafeHttpUrl, placeImageUrl, type PlaceMaterial } from '../api/places'

interface PlaceImageGalleryProps {
  placeId: string
  images: PlaceMaterial[]
}

function imageSourceUrl(placeId: string, image: PlaceMaterial): string | null {
  if (image.revision.media_id) {
    return placeImageUrl(placeId, image.revision.media_id)
  }

  return image.revision.url && isSafeHttpUrl(image.revision.url)
    ? image.revision.url
    : null
}

export default function PlaceImageGallery({
  placeId,
  images,
}: PlaceImageGalleryProps) {
  const galleryImages = images.filter(
    (image) => image.type === 'image' && imageSourceUrl(placeId, image),
  )
  const [activeIndex, setActiveIndex] = useState(0)
  const [isLightboxOpen, setIsLightboxOpen] = useState(false)
  const openButtonRef = useRef<HTMLButtonElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const wasLightboxOpenRef = useRef(false)

  useEffect(() => {
    if (!isLightboxOpen) {
      if (wasLightboxOpenRef.current) {
        openButtonRef.current?.focus()
        wasLightboxOpenRef.current = false
      }
      return
    }

    wasLightboxOpenRef.current = true
    closeButtonRef.current?.focus()
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const handleWindowKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsLightboxOpen(false)
      } else if (event.key === 'ArrowLeft') {
        setActiveIndex((index) =>
          index === 0 ? galleryImages.length - 1 : index - 1,
        )
      } else if (event.key === 'ArrowRight') {
        setActiveIndex((index) => (index + 1) % galleryImages.length)
      }
    }

    window.addEventListener('keydown', handleWindowKeyDown)
    return () => {
      window.removeEventListener('keydown', handleWindowKeyDown)
      document.body.style.overflow = previousOverflow
    }
  }, [galleryImages.length, isLightboxOpen])

  if (galleryImages.length === 0) {
    return null
  }

  const normalizedIndex = Math.min(activeIndex, galleryImages.length - 1)
  const activeImage = galleryImages[normalizedIndex]
  const activeImageUrl = imageSourceUrl(placeId, activeImage)
  const hasSeveralImages = galleryImages.length > 1

  const showPrevious = () => {
    setActiveIndex((index) =>
      index === 0 ? galleryImages.length - 1 : index - 1,
    )
  }

  const showNext = () => {
    setActiveIndex((index) => (index + 1) % galleryImages.length)
  }

  const handleGalleryKeyDown = (event: React.KeyboardEvent<HTMLElement>) => {
    if (event.key === 'ArrowLeft') {
      event.preventDefault()
      showPrevious()
    } else if (event.key === 'ArrowRight') {
      event.preventDefault()
      showNext()
    }
  }

  const closeLightbox = () => setIsLightboxOpen(false)

  return (
    <section
      className="place-gallery"
      aria-labelledby="place-gallery-title"
      onKeyDown={handleGalleryKeyDown}
      tabIndex={0}
    >
      <div className="place-gallery-header">
        <h2 id="place-gallery-title" className="place-gallery-title">
          Фотографии
        </h2>
        <span className="place-gallery-counter" aria-live="polite">
          {normalizedIndex + 1} / {galleryImages.length}
        </span>
      </div>

      <figure className="place-gallery-figure">
        <div className="place-gallery-stage">
          <button
            ref={openButtonRef}
            className="place-gallery-open"
            type="button"
            aria-label={`Открыть фотографию крупно: ${activeImage.title}`}
            onClick={() => setIsLightboxOpen(true)}
          >
            <img src={activeImageUrl ?? ''} alt={activeImage.title} />
          </button>

          {hasSeveralImages && (
            <>
              <button
                className="place-gallery-arrow place-gallery-arrow--previous"
                type="button"
                aria-label="Предыдущая фотография"
                onClick={showPrevious}
              >
                ‹
              </button>
              <button
                className="place-gallery-arrow place-gallery-arrow--next"
                type="button"
                aria-label="Следующая фотография"
                onClick={showNext}
              >
                ›
              </button>
            </>
          )}
        </div>

        <figcaption className="place-gallery-caption">
          <strong>{activeImage.title}</strong>
          {activeImage.source && <span>{activeImage.source}</span>}
          {activeImage.revision.url &&
            isSafeHttpUrl(activeImage.revision.url) && (
              <a
                href={activeImage.revision.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Открыть источник <span aria-hidden="true">↗</span>
              </a>
            )}
        </figcaption>
      </figure>

      {hasSeveralImages && (
        <div className="place-gallery-thumbnails" aria-label="Выбор фотографии">
          {galleryImages.map((image, index) => {
            const thumbnailUrl = imageSourceUrl(placeId, image)
            return (
              <button
                className={`place-gallery-thumbnail${index === normalizedIndex ? ' is-active' : ''}`}
                type="button"
                aria-label={`Показать фотографию ${index + 1}: ${image.title}`}
                aria-pressed={index === normalizedIndex}
                onClick={() => setActiveIndex(index)}
                key={image.id}
              >
                <img src={thumbnailUrl ?? ''} alt="" loading="lazy" />
              </button>
            )
          })}
        </div>
      )}

      {isLightboxOpen && (
        <dialog
          className="place-gallery-lightbox"
          aria-label={`Просмотр фотографии: ${activeImage.title}`}
          open
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              closeLightbox()
            }
          }}
        >
          <div className="place-gallery-lightbox-content">
            <button
              ref={closeButtonRef}
              className="place-gallery-lightbox-close"
              type="button"
              aria-label="Закрыть просмотр фотографии"
              onClick={closeLightbox}
            >
              ×
            </button>
            <img src={activeImageUrl ?? ''} alt={activeImage.title} />
            {hasSeveralImages && (
              <>
                <button
                  className="place-gallery-arrow place-gallery-arrow--previous"
                  type="button"
                  aria-label="Предыдущая фотография в полноэкранном режиме"
                  onClick={showPrevious}
                >
                  ‹
                </button>
                <button
                  className="place-gallery-arrow place-gallery-arrow--next"
                  type="button"
                  aria-label="Следующая фотография в полноэкранном режиме"
                  onClick={showNext}
                >
                  ›
                </button>
              </>
            )}
            <div className="place-gallery-lightbox-caption">
              <strong>{activeImage.title}</strong>
              <span>
                {normalizedIndex + 1} / {galleryImages.length}
              </span>
            </div>
          </div>
        </dialog>
      )}
    </section>
  )
}
