import type { PlaceSummary } from '../api/places'
import type { CuratedRoute } from '../data/curatedRoutes'

interface CuratedRoutesPanelProps {
  routes: readonly CuratedRoute[]
  selectedRoute: CuratedRoute | null
  places: PlaceSummary[]
  isPlacesLoading: boolean
  hasPlacesError: boolean
  onSelectRoute: (routeId: string) => void
  onSelectPlace: (placeId: string) => void
  onBack: () => void
  onClose: () => void
}

function formatPlaceCount(count: number): string {
  const remainder100 = count % 100
  const remainder10 = count % 10
  const noun =
    remainder100 >= 11 && remainder100 <= 14
      ? 'мест'
      : remainder10 === 1
        ? 'место'
        : remainder10 >= 2 && remainder10 <= 4
          ? 'места'
          : 'мест'
  return `${count} ${noun}`
}

export default function CuratedRoutesPanel({
  routes,
  selectedRoute,
  places,
  isPlacesLoading,
  hasPlacesError,
  onSelectRoute,
  onSelectPlace,
  onBack,
  onClose,
}: CuratedRoutesPanelProps) {
  if (selectedRoute === null) {
    return (
      <section className="routes-panel" aria-labelledby="routes-title">
        <div className="place-detail-header">
          <div className="panel-kicker mb-0">Городские прогулки</div>
          <button
            className="place-detail-close"
            type="button"
            aria-label="Закрыть список маршрутов"
            onClick={onClose}
          >
            ×
          </button>
        </div>
        <h1 className="h5 my-2" id="routes-title">
          Маршруты
        </h1>
        <p className="text-secondary">
          Исследуйте связанные места в удобном порядке.
        </p>
        <div className="route-list">
          {routes.map((route) => (
            <button
              className="route-card"
              type="button"
              key={route.id}
              onClick={() => onSelectRoute(route.id)}
            >
              <span className="route-card-city">{route.city}</span>
              <strong>{route.title}</strong>
              <span>{formatPlaceCount(route.placeIds.length)}</span>
            </button>
          ))}
        </div>
      </section>
    )
  }

  const routePlaces = selectedRoute.placeIds.map((placeId) => ({
    placeId,
    place: places.find((place) => place.id === placeId),
  }))
  const distance = selectedRoute.distanceKilometers.toLocaleString('ru-RU', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })

  return (
    <article className="route-detail" aria-labelledby="route-title">
      <div className="place-detail-header">
        <div className="panel-kicker mb-0">
          Маршрут · {selectedRoute.city}
        </div>
        <button
          className="place-detail-close"
          type="button"
          aria-label="Закрыть маршрут"
          onClick={onClose}
        >
          ×
        </button>
      </div>
      <h1 className="h5 my-2" id="route-title">
        {selectedRoute.title}
      </h1>
      <p className="route-description">{selectedRoute.description}</p>
      <div className="route-summary" aria-label="Параметры маршрута">
        <span>
          <strong>{distance} км</strong>
          <small>длина пути</small>
        </span>
        <span>
          <strong>около {selectedRoute.walkingTimeMinutes} минут</strong>
          <small>без остановок</small>
        </span>
      </div>
      <a
        className="btn route-navigation-link"
        href={selectedRoute.navigationUrl}
        target="_blank"
        rel="noreferrer"
      >
        Открыть пеший маршрут в Яндекс Картах
      </a>
      <p className="route-map-note">
        Линия на карте идёт по пешеходным дорогам. Перед прогулкой проверяйте доступность
        проходов на месте.
      </p>

      <h2 className="route-stops-title">Остановки</h2>
      {isPlacesLoading && <p className="text-secondary">Загружаем места…</p>}
      {!isPlacesLoading && hasPlacesError && (
        <div className="alert alert-warning" role="alert">
          Не удалось загрузить остановки маршрута.
        </div>
      )}
      {!isPlacesLoading && !hasPlacesError && (
        <ol className="route-stops">
          {routePlaces.map(({ placeId, place }, index) => (
            <li key={placeId}>
              <button
                type="button"
                onClick={() => onSelectPlace(placeId)}
                disabled={!place}
              >
                <span className="route-stop-number" aria-hidden="true">
                  {index + 1}
                </span>
                <span>{place?.title ?? 'Место пока недоступно'}</span>
              </button>
            </li>
          ))}
        </ol>
      )}

      <div className="route-links" aria-label="Материалы маршрута">
        {selectedRoute.links.map((link) => (
          <a key={link.url} href={link.url} target="_blank" rel="noreferrer">
            {link.label}
          </a>
        ))}
      </div>
      <p className="route-attribution">
        Пешеходный путь рассчитан Valhalla по данным{' '}
        <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">
          OpenStreetMap
        </a>
        .
      </p>
      <button className="btn btn-link route-back" type="button" onClick={onBack}>
        Все маршруты
      </button>
    </article>
  )
}
