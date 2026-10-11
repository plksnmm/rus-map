export interface CuratedRouteLink {
  label: string
  url: string
}

export interface CuratedRoute {
  id: string
  title: string
  city: string
  description: string
  placeIds: readonly string[]
  links: readonly CuratedRouteLink[]
}

export const curatedRoutes: readonly CuratedRoute[] = [
  {
    id: 'yaroslavl-red-perekop',
    title: '«Красный Перекоп»',
    city: 'Ярославль',
    description:
      'Прогулка по местам рабочей истории Ярославской Большой мануфактуры: от фабричного городка и памяти о стачках к исторической территории предприятия.',
    placeIds: [
      '531c004b-e7d4-40a4-9605-13481401931a',
      '1ee1a2eb-b60f-4b31-bc7d-81afe5664724',
      '38ed1b06-8e68-4ca1-96d5-2c47baf66d78',
    ],
    links: [
      {
        label: 'Видеоэкскурсия',
        url: 'https://youtu.be/R3Q6pv-eEm4',
      },
      {
        label: 'Материал «Руси пролетарской»',
        url: 'https://t.me/rus_proletarskaya/114',
      },
    ],
  },
]
