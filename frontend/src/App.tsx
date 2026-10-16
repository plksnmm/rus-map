import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react'
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
import CuratedRoutesPanel from './components/CuratedRoutesPanel'
import PlaceImageGallery from './components/PlaceImageGallery'
import PlaceMaterials from './components/PlaceMaterials'
import PlaceSubmissionForm, {
  type MapLocation,
} from './components/PlaceSubmissionForm'
import { curatedRoutes } from './data/curatedRoutes'
import { decodeRoutePath } from './map/routeGeoJson'

const MapView = lazy(() => import('./components/MapView'))

type MobileSheetState = 'compact' | 'half' | 'expanded'

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
  const [isRoutesOpen, setIsRoutesOpen] = useState(false)
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null)
  const [mobileRouteSheetState, setMobileRouteSheetState] =
    useState<MobileSheetState>('half')

  const selectedRoute = useMemo(
    () =>
      curatedRoutes.find((route) => route.id === selectedRouteId) ?? null,
    [selectedRouteId],
  )
  const routePlaces = useMemo(
    () =>
      selectedRoute?.placeIds
        .map((placeId) => places.find((place) => place.id === placeId))
        .filter((place): place is PlaceSummary => place !== undefined) ?? [],
    [places, selectedRoute],
  )
  const routePath = useMemo(
    () => decodeRoutePath(selectedRoute?.pathSegments ?? []),
    [selectedRoute],
  )

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
    setIsRoutesOpen(false)
    setSelectedRouteId(null)
    setIsSubmissionOpen(true)
    setSubmissionSent(false)
  }, [handleClosePlace])

  const handleCloseSubmission = useCallback(() => {
    setIsSubmissionOpen(false)
    setSubmissionLocation(null)
    setSubmissionMapFocus(null)
    setSubmissionSent(false)
  }, [])

  const handleCloseRoutes = useCallback(() => {
    handleClosePlace()
    setIsRoutesOpen(false)
    setSelectedRouteId(null)
    setMobileRouteSheetState('half')
  }, [handleClosePlace])

  const handleSelectRoute = useCallback((routeId: string) => {
    setSelectedRouteId(routeId)
    setMobileRouteSheetState('compact')
  }, [])

  const handleToggleMobileRouteSheet = useCallback(() => {
    setMobileRouteSheetState((current) =>
      current === 'compact' ? 'half' : 'compact',
    )
  }, [])

  const handleToggleMobileRouteSecondaryDetails = useCallback(() => {
    setMobileRouteSheetState((current) =>
      current === 'expanded' ? 'half' : 'expanded',
    )
  }, [])

  const handleToggleRoutes = useCallback(() => {
    if (isRoutesOpen) {
      handleCloseRoutes()
      return
    }
    handleClosePlace()
    setIsSubmissionOpen(false)
    setSubmissionLocation(null)
    setSubmissionMapFocus(null)
    setSubmissionSent(false)
    setIsRoutesOpen(true)
    setMobileRouteSheetState('half')
  }, [handleClosePlace, handleCloseRoutes, isRoutesOpen])

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
          <button
            className={`btn app-route-button btn-sm${isRoutesOpen ? ' is-active' : ''}`}
            type="button"
            aria-label={isRoutesOpen ? 'Закрыть маршрут' : 'Маршруты'}
            onClick={handleToggleRoutes}
          >
            <span className="route-button-wide-label">
              {isRoutesOpen ? 'Закрыть маршрут' : 'Маршруты'}
            </span>
            <span className="route-button-mobile-label">
              {isRoutesOpen ? 'Закрыть' : 'Маршруты'}
            </span>
          </button>
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
          <details className="app-mobile-menu">
            <summary aria-label="Другие действия">•••</summary>
            <div className="app-mobile-menu-popover">
              <a
                href={`${import.meta.env.BASE_URL}admin`}
                aria-label="Открыть редакторскую"
              >
                Редакторская
              </a>
              <button
                type="button"
                aria-label={
                  isSubmissionOpen
                    ? 'Закрыть форму из мобильного меню'
                    : 'Предложить место через мобильное меню'
                }
                onClick={(event) => {
                  event.currentTarget.closest('details')?.removeAttribute('open')
                  if (isSubmissionOpen) {
                    handleCloseSubmission()
                  } else {
                    handleOpenSubmission()
                  }
                }}
              >
                {isSubmissionOpen ? 'Закрыть форму' : 'Предложить место'}
              </button>
            </div>
          </details>
        </div>
      </header>

      <section className="map-layout" aria-label="Карта мест">
        {!isLoading && !hasError && places.length > 0 && (
          <div className="mobile-map-status" role="status">
            На карте: {places.length}
          </div>
        )}
        <aside
          className={`place-panel shadow-sm${selectedPlaceId || isSubmissionOpen || isRoutesOpen ? ' place-panel--detail' : ' place-panel--overview'}${selectedPlaceId ? ' place-panel--place' : ''}${isSubmissionOpen ? ' place-panel--submission' : ''}${isRoutesOpen && selectedRoute === null ? ' place-panel--routes' : ''}${selectedRoute ? ` place-panel--route mobile-sheet--${mobileRouteSheetState}` : ''}`}
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
          ) : selectedPlaceId !== null ? (
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
          ) : isRoutesOpen ? (
            <CuratedRoutesPanel
              routes={curatedRoutes}
              selectedRoute={selectedRoute}
              places={places}
              isPlacesLoading={isLoading}
              hasPlacesError={hasError}
              onSelectRoute={handleSelectRoute}
              onSelectPlace={handleSelectPlace}
              onBack={() => {
                setSelectedRouteId(null)
                setMobileRouteSheetState('half')
              }}
              onClose={handleCloseRoutes}
              mobileSheetState={mobileRouteSheetState}
              onToggleMobileSheet={handleToggleMobileRouteSheet}
              onToggleMobileSecondaryDetails={
                handleToggleMobileRouteSecondaryDetails
              }
            />
          ) : (
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
            routePlaces={routePlaces}
            routePath={routePath}
            routePanelState={mobileRouteSheetState}
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
