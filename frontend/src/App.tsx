import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import {
  fetchPlace,
  fetchPlaceMaterials,
  fetchPlaces,
  type PlaceMaterial,
  type PlaceDetail,
  type PlaceSummary,
} from './api/places'
import type { GeocodingResult } from './api/geocoding'
import './App.css'
import AdminApp from './AdminApp'
import PlaceImageGallery from './components/PlaceImageGallery'
import PlaceMaterials from './components/PlaceMaterials'
import PlaceSubmissionForm, {
  type MapLocation,
} from './components/PlaceSubmissionForm'

const MapView = lazy(() => import('./components/MapView'))

function PublicMapApp() {
  const [places, setPlaces] = useState<PlaceSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null)
  const [selectedPlace, setSelectedPlace] = useState<PlaceDetail | null>(null)
  const [isDetailLoading, setIsDetailLoading] = useState(false)
  const [hasDetailError, setHasDetailError] = useState(false)
  const [materials, setMaterials] = useState<PlaceMaterial[]>([])
  const [isMaterialsLoading, setIsMaterialsLoading] = useState(false)
  const [hasMaterialsError, setHasMaterialsError] = useState(false)
  const [isSubmissionOpen, setIsSubmissionOpen] = useState(false)
  const [submissionLocation, setSubmissionLocation] =
    useState<MapLocation | null>(null)
  const [submissionMapFocus, setSubmissionMapFocus] =
    useState<GeocodingResult | null>(null)
  const [submissionSent, setSubmissionSent] = useState(false)

  const handleSelectPlace = useCallback((placeId: string) => {
    setIsSubmissionOpen(false)
    setSubmissionLocation(null)
    setSubmissionMapFocus(null)
    setSubmissionSent(false)
    setSelectedPlaceId(placeId)
    setSelectedPlace(null)
    setIsDetailLoading(true)
    setHasDetailError(false)
    setMaterials([])
    setIsMaterialsLoading(true)
    setHasMaterialsError(false)
  }, [])

  const handleClosePlace = useCallback(() => {
    setSelectedPlaceId(null)
    setSelectedPlace(null)
    setIsDetailLoading(false)
    setHasDetailError(false)
    setMaterials([])
    setIsMaterialsLoading(false)
    setHasMaterialsError(false)
  }, [])

  const handleOpenSubmission = useCallback(() => {
    handleClosePlace()
    setIsSubmissionOpen(true)
    setSubmissionSent(false)
  }, [handleClosePlace])

  const handleCloseSubmission = useCallback(() => {
    setIsSubmissionOpen(false)
    setSubmissionLocation(null)
    setSubmissionMapFocus(null)
    setSubmissionSent(false)
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    let isActive = true

    fetchPlaces(controller.signal)
      .then((response) => {
        if (!isActive) {
          return
        }

        setPlaces(response.items)
        setHasError(false)
      })
      .catch((error: unknown) => {
        if (
          !isActive ||
          (error instanceof DOMException && error.name === 'AbortError')
        ) {
          return
        }

        setHasError(true)
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
  }, [])

  useEffect(() => {
    if (selectedPlaceId === null) {
      return
    }

    const controller = new AbortController()
    let isActive = true

    fetchPlace(selectedPlaceId, controller.signal)
      .then((place) => {
        if (isActive) {
          setSelectedPlace(place)
        }
      })
      .catch((error: unknown) => {
        if (
          !isActive ||
          (error instanceof DOMException && error.name === 'AbortError')
        ) {
          return
        }

        setHasDetailError(true)
      })
      .finally(() => {
        if (isActive) {
          setIsDetailLoading(false)
        }
      })

    return () => {
      isActive = false
      controller.abort()
    }
  }, [selectedPlaceId])

  useEffect(() => {
    if (selectedPlaceId === null) {
      return
    }

    const controller = new AbortController()
    let isActive = true

    fetchPlaceMaterials(selectedPlaceId, controller.signal)
      .then((response) => {
        if (isActive) {
          setMaterials(response.items)
        }
      })
      .catch((error: unknown) => {
        if (
          !isActive ||
          (error instanceof DOMException && error.name === 'AbortError')
        ) {
          return
        }

        setHasMaterialsError(true)
      })
      .finally(() => {
        if (isActive) {
          setIsMaterialsLoading(false)
        }
      })

    return () => {
      isActive = false
      controller.abort()
    }
  }, [selectedPlaceId])

  return (
    <main className="app-shell">
      <header className="navbar navbar-dark app-header px-3">
        <div className="brand-group">
          <span
            className="brand-mark"
            role="img"
            aria-label="Логотип «Русь пролетарская»"
          />
          <div className="brand-copy">
            <span className="navbar-brand mb-0 h1">Русь пролетарская</span>
            <span className="app-subtitle d-none d-sm-block">
              Карта мест пролетарской силы
            </span>
          </div>
        </div>
        <div className="app-header-actions">
          <a
            className="btn app-admin-link btn-sm"
            href={`${import.meta.env.BASE_URL}admin`}
          >
            Редакторская
          </a>
          <button
            className={`btn app-add-button btn-sm${isSubmissionOpen ? ' is-active' : ''}`}
            type="button"
            onClick={isSubmissionOpen ? handleCloseSubmission : handleOpenSubmission}
          >
            {isSubmissionOpen ? 'Закрыть форму' : 'Добавить место'}
          </button>
        </div>
      </header>

      <section className="map-layout" aria-label="Карта мест">
        <aside
          className={`place-panel shadow-sm${selectedPlaceId || isSubmissionOpen ? ' place-panel--detail' : ''}`}
        >
          {isSubmissionOpen ? (
            submissionSent ? (
              <div className="submission-success" role="status">
                <div className="submission-success-mark" aria-hidden="true">
                  ✓
                </div>
                <div className="panel-kicker">Заявка отправлена</div>
                <h1 className="h5 my-2">Спасибо за новую точку</h1>
                <p>
                  Она уже в очереди редактора и появится на карте после
                  проверки.
                </p>
                <div className="submission-actions">
                  <button
                    className="btn app-submit-button"
                    type="button"
                    onClick={() => {
                      setSubmissionLocation(null)
                      setSubmissionMapFocus(null)
                      setSubmissionSent(false)
                    }}
                  >
                    Предложить ещё место
                  </button>
                  <button
                    className="btn btn-link"
                    type="button"
                    onClick={handleCloseSubmission}
                  >
                    Вернуться к карте
                  </button>
                </div>
              </div>
            ) : (
              <PlaceSubmissionForm
                location={submissionLocation}
                onCancel={handleCloseSubmission}
                onLocationCleared={() => {
                  setSubmissionLocation(null)
                  setSubmissionMapFocus(null)
                }}
                onLocationFound={(result) => {
                  setSubmissionLocation({
                    latitude: result.latitude,
                    longitude: result.longitude,
                  })
                  setSubmissionMapFocus({ ...result })
                }}
                onSubmitted={() => setSubmissionSent(true)}
              />
            )
          ) : selectedPlaceId === null ? (
            <>
              <div className="panel-kicker">Народный архив</div>
              <h1 className="h5 mb-2 text-uppercase">
                Исследуй историю вокруг
              </h1>
              <p className="text-secondary mb-3">
                Здесь появятся памятники, заводы, культурные пространства и
                маршруты.
              </p>
              {isLoading && (
                <div className="alert alert-light border mb-0" role="status">
                  Загружаем места…
                </div>
              )}
              {!isLoading && hasError && (
                <div className="alert alert-warning mb-0" role="alert">
                  Не удалось загрузить места. Карта продолжает работать —
                  попробуйте обновить страницу позже.
                </div>
              )}
              {!isLoading && !hasError && places.length === 0 && (
                <div className="alert alert-light border mb-0" role="status">
                  На карте пока нет мест.
                </div>
              )}
              {!isLoading && !hasError && places.length > 0 && (
                <div className="place-count" role="status">
                  На карте мест: <strong>{places.length}</strong>
                </div>
              )}
            </>
          ) : (
            <article className="place-detail" aria-live="polite">
              <div className="place-detail-header">
                <div className="panel-kicker mb-0">Карточка места</div>
                <button
                  className="place-detail-close"
                  type="button"
                  aria-label="Закрыть карточку места"
                  onClick={handleClosePlace}
                >
                  ×
                </button>
              </div>
              {isDetailLoading && (
                <div className="alert alert-light border mb-0" role="status">
                  Загружаем информацию…
                </div>
              )}
              {!isDetailLoading && hasDetailError && (
                <div className="alert alert-warning mb-0" role="alert">
                  Не удалось загрузить информацию о месте. Карта продолжает
                  работать.
                </div>
              )}
              {!isDetailLoading && selectedPlace && (
                <>
                  <h1 className="h5 my-2">{selectedPlace.title}</h1>
                  <PlaceImageGallery
                    key={selectedPlace.id}
                    placeId={selectedPlace.id}
                    images={materials.filter(
                      (material) => material.type === 'image',
                    )}
                  />
                  {selectedPlace.description ? (
                    <p className="place-detail-description mb-0">
                      {selectedPlace.description}
                    </p>
                  ) : (
                    <p className="text-secondary mb-0">
                      Описание пока не добавлено.
                    </p>
                  )}
                  <PlaceMaterials
                    materials={materials}
                    isLoading={isMaterialsLoading}
                    hasError={hasMaterialsError}
                  />
                </>
              )}
            </article>
          )}
        </aside>

        <Suspense
          fallback={
            <div className="map-loading" role="status">
              Загружаем карту…
            </div>
          }
        >
          <MapView
            places={places}
            onSelectPlace={handleSelectPlace}
            isSelectingLocation={isSubmissionOpen && !submissionSent}
            selectedLocation={submissionLocation}
            focusLocation={submissionMapFocus}
            onSelectLocation={(location) => {
              setSubmissionLocation(location)
              setSubmissionMapFocus(null)
            }}
          />
        </Suspense>
      </section>
    </main>
  )
}

function isAdminPath(pathname: string): boolean {
  const adminPath = `${import.meta.env.BASE_URL}admin`.replace(/\/$/, '')
  const normalizedPath = pathname.replace(/\/$/, '')
  return normalizedPath === adminPath || normalizedPath.startsWith(`${adminPath}/`)
}

function App() {
  return isAdminPath(window.location.pathname) ? <AdminApp /> : <PublicMapApp />
}

export default App
