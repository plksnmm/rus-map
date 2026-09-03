import { lazy, Suspense, useEffect, useState } from 'react'
import { fetchPlaces, type PlaceSummary } from './api/places'
import './App.css'

const MapView = lazy(() => import('./components/MapView'))

function App() {
  const [places, setPlaces] = useState<PlaceSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)

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
        <button className="btn app-add-button btn-sm" type="button" disabled>
          Добавить место
        </button>
      </header>

      <section className="map-layout" aria-label="Карта мест">
        <aside className="place-panel shadow-sm">
          <div className="panel-kicker">Народный архив</div>
          <h1 className="h5 mb-2 text-uppercase">Исследуй историю вокруг</h1>
          <p className="text-secondary mb-3">
            Здесь появятся памятники, заводы, культурные пространства и маршруты.
          </p>
          {isLoading && (
            <div className="alert alert-light border mb-0" role="status">
              Загружаем места…
            </div>
          )}
          {!isLoading && hasError && (
            <div className="alert alert-warning mb-0" role="alert">
              Не удалось загрузить места. Карта продолжает работать — попробуйте
              обновить страницу позже.
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
        </aside>

        <Suspense
          fallback={
            <div className="map-loading" role="status">
              Загружаем карту…
            </div>
          }
        >
          <MapView places={places} />
        </Suspense>
      </section>
    </main>
  )
}

export default App
