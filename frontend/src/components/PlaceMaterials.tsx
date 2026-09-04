import { isSafeHttpUrl, type PlaceMaterial } from '../api/places'

interface PlaceMaterialsProps {
  materials: PlaceMaterial[]
  isLoading: boolean
  hasError: boolean
}

const materialTypeLabels: Record<PlaceMaterial['type'], string> = {
  text: 'Текст',
  external_link: 'Ссылка',
  image: 'Изображение',
  video: 'Видео',
  audio: 'Аудио',
}

const linkLabels: Record<Exclude<PlaceMaterial['type'], 'text'>, string> = {
  external_link: 'Открыть источник',
  image: 'Открыть изображение',
  video: 'Смотреть видео',
  audio: 'Слушать аудио',
}

function MaterialLink({ material }: { material: PlaceMaterial }) {
  const url = material.revision.url

  if (material.type === 'text' || url === null || !isSafeHttpUrl(url)) {
    return null
  }

  return (
    <>
      {material.type === 'image' && (
        <a href={url} target="_blank" rel="noopener noreferrer">
          <img
            className="place-material-image"
            src={url}
            alt={material.title}
            loading="lazy"
          />
        </a>
      )}
      <a
        className="place-material-link"
        href={url}
        target="_blank"
        rel="noopener noreferrer"
      >
        {linkLabels[material.type]}
        <span aria-hidden="true"> ↗</span>
      </a>
    </>
  )
}

export default function PlaceMaterials({
  materials,
  isLoading,
  hasError,
}: PlaceMaterialsProps) {
  return (
    <section className="place-materials" aria-labelledby="place-materials-title">
      <h2 id="place-materials-title" className="place-materials-title">
        Материалы
      </h2>

      {isLoading && (
        <div className="alert alert-light border mb-0" role="status">
          Загружаем материалы…
        </div>
      )}

      {!isLoading && hasError && (
        <div className="alert alert-warning mb-0" role="alert">
          Не удалось загрузить материалы. Основная информация о месте остаётся
          доступна.
        </div>
      )}

      {!isLoading && !hasError && materials.length === 0 && (
        <p className="text-secondary mb-0">Материалы пока не добавлены.</p>
      )}

      {!isLoading && !hasError && materials.length > 0 && (
        <div className="place-material-list">
          {materials.map((material) => (
            <article className="place-material" key={material.id}>
              <div className="place-material-type">
                {materialTypeLabels[material.type]}
              </div>
              <h3 className="place-material-heading">{material.title}</h3>
              {material.source && (
                <div className="place-material-source">
                  Источник: {material.source}
                </div>
              )}
              {material.type === 'text' && material.revision.content && (
                <p className="place-material-content mb-0">
                  {material.revision.content}
                </p>
              )}
              <MaterialLink material={material} />
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
