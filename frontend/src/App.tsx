import { lazy, Suspense } from 'react'
import './App.css'

const MapView = lazy(() => import('./components/MapView'))

function App() {
  return (
    <main className="app-shell">
      <header className="navbar navbar-dark app-header px-3">
        <div>
          <span className="navbar-brand mb-0 h1">Русь пролетарская</span>
          <span className="app-subtitle d-none d-sm-inline">
            Карта мест пролетарской силы
          </span>
        </div>
        <button className="btn btn-light btn-sm" type="button" disabled>
          Добавить место
        </button>
      </header>

      <section className="map-layout" aria-label="Карта мест">
        <aside className="place-panel shadow-sm">
          <h1 className="h5 mb-2">Исследуй историю вокруг</h1>
          <p className="text-secondary mb-3">
            Здесь появятся памятники, заводы, культурные пространства и маршруты.
          </p>
          <div className="alert alert-light border mb-0" role="status">
            Места из базы данных подключим в следующей задаче.
          </div>
        </aside>

        <Suspense
          fallback={
            <div className="map-loading" role="status">
              Загружаем карту…
            </div>
          }
        >
          <MapView />
        </Suspense>
      </section>
    </main>
  )
}

export default App
