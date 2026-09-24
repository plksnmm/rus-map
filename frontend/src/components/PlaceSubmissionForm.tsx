import { useState, type FormEvent } from 'react'
import {
  GeocodingApiError,
  searchAddress,
  type GeocodingResult,
} from '../api/geocoding'
import { submitPlace } from '../api/submissions'

export interface MapLocation {
  latitude: number
  longitude: number
}

interface PlaceSubmissionFormProps {
  location: MapLocation | null
  onCancel: () => void
  onLocationFound: (result: GeocodingResult) => void
  onSubmitted: () => void
}

function parseSourceUrls(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map((url) => url.trim())
    .filter(Boolean)
}

export default function PlaceSubmissionForm({
  location,
  onCancel,
  onLocationFound,
  onSubmitted,
}: PlaceSubmissionFormProps) {
  const [address, setAddress] = useState('')
  const [selectedAddress, setSelectedAddress] = useState<string | null>(null)
  const [addressResults, setAddressResults] = useState<GeocodingResult[]>([])
  const [isSearchingAddress, setIsSearchingAddress] = useState(false)
  const [addressSearchAttempted, setAddressSearchAttempted] = useState(false)
  const [addressError, setAddressError] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [sourceUrls, setSourceUrls] = useState('')
  const [website, setWebsite] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleAddressSearch() {
    const query = address.trim()
    if (query.length < 3 || isSearchingAddress) {
      return
    }

    setIsSearchingAddress(true)
    setAddressError(null)
    setAddressSearchAttempted(true)
    try {
      const response = await searchAddress(query)
      setAddressResults(response.items)
    } catch (requestError) {
      setAddressResults([])
      setAddressError(
        requestError instanceof GeocodingApiError && requestError.status === 429
          ? 'Поиск занят. Подождите секунду и попробуйте снова.'
          : 'Не удалось найти адрес. Можно указать точку на карте вручную.',
      )
    } finally {
      setIsSearchingAddress(false)
    }
  }

  function selectAddressResult(result: GeocodingResult) {
    setSelectedAddress(result.display_name)
    setAddressResults([])
    setAddressSearchAttempted(false)
    setAddressError(null)
    onLocationFound(result)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!location) {
      setError('Сначала укажите место на карте.')
      return
    }

    setIsSubmitting(true)
    setError(null)
    try {
      await submitPlace({
        title: title.trim(),
        description: description.trim() || null,
        latitude: location.latitude,
        longitude: location.longitude,
        address: selectedAddress ?? (address.trim() || null),
        source_urls: parseSourceUrls(sourceUrls),
        website,
      })
      onSubmitted()
    } catch (requestError) {
      const status =
        requestError instanceof Error && 'status' in requestError
          ? requestError.status
          : null
      setError(
        status === 429
          ? 'Слишком много заявок. Попробуйте отправить позже.'
          : 'Не удалось отправить заявку. Проверьте поля и попробуйте ещё раз.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form className="submission-form" onSubmit={handleSubmit}>
      <div className="place-detail-header">
        <div className="panel-kicker mb-0">Предложить место</div>
        <button
          className="place-detail-close"
          type="button"
          aria-label="Закрыть форму добавления места"
          onClick={onCancel}
        >
          ×
        </button>
      </div>
      <h1 className="h5 my-2">Добавьте историю на карту</h1>
      <p className="submission-intro">
        Найдите адрес или укажите точку на карте, затем расскажите о месте.
        Редактор проверит заявку перед публикацией.
      </p>

      <div className="submission-address-search">
        <label className="form-label" htmlFor="submission-address">
          Адрес или название места
        </label>
        <div className="submission-address-controls">
          <input
            className="form-control"
            id="submission-address"
            maxLength={500}
            placeholder="Например: Москва, Перовская улица, 66"
            value={address}
            disabled={isSearchingAddress}
            onChange={(event) => {
              setAddress(event.target.value)
              setSelectedAddress(null)
              setAddressResults([])
              setAddressSearchAttempted(false)
              setAddressError(null)
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                void handleAddressSearch()
              }
            }}
          />
          <button
            className="btn submission-search-button"
            type="button"
            disabled={address.trim().length < 3 || isSearchingAddress}
            onClick={() => void handleAddressSearch()}
          >
            {isSearchingAddress ? 'Ищем…' : 'Найти'}
          </button>
        </div>
        {addressError && (
          <div className="submission-address-message" role="alert">
            {addressError}
          </div>
        )}
        {!isSearchingAddress &&
          !addressError &&
          addressSearchAttempted &&
          addressResults.length === 0 && (
            <div className="submission-address-message" role="status">
              Ничего не найдено. Уточните запрос или выберите точку вручную.
            </div>
          )}
        {addressResults.length > 0 && (
          <ul className="submission-address-results" aria-label="Найденные адреса">
            {addressResults.map((result) => (
              <li key={`${result.latitude}:${result.longitude}:${result.display_name}`}>
                <button type="button" onClick={() => selectAddressResult(result)}>
                  {result.display_name}
                </button>
              </li>
            ))}
          </ul>
        )}
        {selectedAddress && (
          <div className="submission-selected-address" role="status">
            <strong>Выбрано:</strong> {selectedAddress}
          </div>
        )}
        <div className="submission-geocoding-attribution">
          Поиск: OpenStreetMap Nominatim ·{' '}
          <a
            href="https://www.openstreetmap.org/copyright"
            target="_blank"
            rel="noreferrer"
          >
            © участники OpenStreetMap
          </a>
        </div>
      </div>

      <div className={`submission-location${location ? ' is-selected' : ''}`}>
        <span className="submission-location-marker" aria-hidden="true" />
        {location ? (
          <span>
            Координаты: {location.latitude.toFixed(5)},{' '}
            {location.longitude.toFixed(5)}
          </span>
        ) : (
          <span>Или нажмите на нужное место на карте</span>
        )}
      </div>

      <label className="form-label" htmlFor="submission-title">
        Название места <span aria-hidden="true">*</span>
      </label>
      <input
        className="form-control"
        id="submission-title"
        maxLength={200}
        required
        value={title}
        onChange={(event) => setTitle(event.target.value)}
      />

      <label className="form-label" htmlFor="submission-description">
        Что здесь находилось или происходит?
      </label>
      <textarea
        className="form-control"
        id="submission-description"
        maxLength={10000}
        rows={4}
        value={description}
        onChange={(event) => setDescription(event.target.value)}
      />

      <label className="form-label" htmlFor="submission-sources">
        Ссылки на источники
      </label>
      <textarea
        className="form-control"
        id="submission-sources"
        placeholder={'Одна ссылка в строке\nhttps://…'}
        rows={3}
        value={sourceUrls}
        onChange={(event) => setSourceUrls(event.target.value)}
      />
      <div className="form-text">До 10 ссылок на публикации, фото или видео.</div>

      <div className="submission-honeypot" aria-hidden="true">
        <label htmlFor="submission-website">Ваш сайт</label>
        <input
          id="submission-website"
          tabIndex={-1}
          autoComplete="off"
          value={website}
          onChange={(event) => setWebsite(event.target.value)}
        />
      </div>

      {error && (
        <div className="alert alert-warning mb-0" role="alert">
          {error}
        </div>
      )}

      <div className="submission-actions">
        <button
          className="btn app-submit-button"
          type="submit"
          disabled={!location || !title.trim() || isSubmitting}
        >
          {isSubmitting ? 'Отправляем…' : 'Отправить на проверку'}
        </button>
        <button className="btn btn-link" type="button" onClick={onCancel}>
          Отмена
        </button>
      </div>
    </form>
  )
}
