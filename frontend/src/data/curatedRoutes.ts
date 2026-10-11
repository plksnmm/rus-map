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
  pathSegments: readonly string[]
  distanceKilometers: number
  walkingTimeMinutes: number
  navigationUrl: string
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
    pathSegments: [
      'yuwzlBw_{~jAAzd@C`iA[bKQxFw@fDiApB}@l@iAZkOtAgu@t@yCbI{Ah@eDkEyRxC_OjEXfB]rWaAng@oLve@gFrTeKjc@wDjH}BnIkDvP_Kj]g@fB{A|DcDzH`DnBvItJsC`VEbJhLnbAqACGhPuCzJtCtSpFz\\zE~ZtCdNnIx_@TrFTlGlIbh@ExK|Hfg@hK~d@rDwB|OwL',
      '}rzzlBula~jA}OvLsDvBiK_e@}Hgg@iDvBk_@|WsD|CoItGeEuVwZtZuY`[mO~QkH~J{b@vg@{n@bv@kd@`i@QRaBlBe]}|AcCxCuV~Z_EuMu`@_qAeHuUeAuCw@oNoHwh@sv@diA}BfD',
    ],
    distanceKilometers: 2.336,
    walkingTimeMinutes: 30,
    navigationUrl:
      'https://yandex.ru/maps/?rtext=57.602525%2C39.8438529~57.6038212%2C39.8303953~57.611773%2C39.830268&rtt=pd',
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
