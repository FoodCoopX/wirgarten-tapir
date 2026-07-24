#let entries = if "entries" in sys.inputs.keys() {
  json(bytes(sys.inputs.at("entries")))
} else {
  json("location_routes_entries.json")
}

// TODO
#let contact = (
  "name": "Nick",
  "email": "info@biotop-oberland.de",
  "phone": "0123-45678910",
)

#set page(
  margin: (x: 1.5cm, y: 2cm),
)



#let total-cell = (rowspan: 1, content) => table.cell(
  stroke: (y: 1pt),
  fill: gray.lighten(50%),
  rowspan: rowspan,
  breakable: false,
  content,
)
#let pickup-cell = content => table.cell(
  stroke: (y: 1pt),
  content,
)

#let products = (
  entries
    .fold((:), (acc, route) => {
      for location in route.pickup_locations {
        for sub in location.subscriptions {
          for p in sub.products {
            let key = p.name
            let current = acc.at(key, default: 0) + p.quantity
            acc.insert(key, current)
          }
        }
      }
      return acc
    })
    .pairs()
    .sorted(key: p => p.at(0))
)
= #products.map(p => p.at(0) + " " + str(p.at(1))).join(" / ") #h(1fr) KW #datetime.today().display("[week_number]")

#table(
  columns: products.len() + 2,
  stroke: none,
  ..for route in entries {
    let sum_by_location_product = route.pickup_locations.fold((:), (
      locations,
      location,
    ) => {
      let sum_by_product = location.subscriptions.fold((:), (acc, sub) => {
        for p in sub.products {
          let key = p.name
          let current = acc.at(key, default: 0) + p.quantity
          acc.insert(key, current)
        }
        return acc
      })
      locations.insert(location.name, sum_by_product)
      return locations
    })

    (
      table.header(
        [],
        [],
        ..for product in products {
          (align(center, text(fill: luma(30%), size: .7em, product.at(0))),)
        },
      ),

      total-cell(
        rowspan: route.pickup_locations.len() + 1,
        [],
      ),
      total-cell([*#route.route_name*]),
      ..for product in products {
        (
          total-cell(align(right, strong(str(sum_by_location_product
            .pairs()
            .fold(0, (
              acc,
              (_, sum_by_product),
            ) => {
              acc + sum_by_product.at(product.at(0), default: 0)
            }))))),
        )
      },

      ..for location in route.pickup_locations {
        (
          pickup-cell(location.name),
          ..for product in products {
            (
              pickup-cell(align(right, str(
                sum_by_location_product
                  .at(location.name)
                  .at(product.at(0), default: "-"),
              ))),
            )
          },
        )
      },
    )
  }
)
#for location in entries.fold((), (acc, route) => {
  acc + route.pickup_locations
}) [
  #pagebreak(weak: true)
  #counter(page).update(1)
  #set page(
    footer: context [
      KW #datetime.today().display("[week_number]")
      #h(1fr)
      #location.name
      #h(1fr)
      #counter(page).display() / #counter(page).at(label(location.name)).at(0)
    ],
  )

  = #location.name #h(1fr) KW #datetime.today().display("[week_number]")

  #location.street\
  #location.postcode #location.city


  #let sums = (
    location
      .subscriptions
      .fold((:), (acc, sub) => {
        for p in sub.products {
          let key = p.name
          let current = acc.at(key, default: 0) + p.quantity
          acc.insert(key, current)
        }
        return acc
      })
      .pairs()
      .sorted(key: p => p.at(0))
  )

  #strong(table(
    columns: (auto, auto),
    stroke: (x, y) => (
      left: if x == 0 { 0.5pt } else { 0pt },
      right: .5pt,
      top: .5pt,
      bottom: .5pt,
    ),
    fill: gray.lighten(50%),
    ..if location.route_info != "" {
      (
        table.cell(colspan: 2, fill: none)[
          #location.route_info
        ],
      )
    },
    ..for (name, qty) in sums {
      ("Summe " + name, align(right, str(qty)))
    },
  ))

  == Keine Kiste mehr da, oder nur noch eine falsche Größe?

  #box(width: 100% - 11em)[
    - Hast Du unter den *Tüchern* und *leeren Kisten* nachgeschaut?
    - Kiste mitnehmen, auch wenn Größe nicht passt und Haken fehlen
    - Bitte Info an uns: Anrufen, SMS oder Mail mit Name / Verteilstation / Kistengröße
    - Kontakt: #contact.name #contact.phone / #contact.email
  ]
  #place(right, dy: -7em)[
    #let txt = box(inset: .5em, width: 10em)[
      *Bestätige hier den Erhalt Deines Biotop-Ernteanteils (bitte ankreuzen)*
    ]
    #context {
      txt
      let size = measure(txt)
      place(right, dx: 0pt, dy: 0pt, polygon(
        //fill: blue.lighten(80%),
        stroke: black,
        (-size.width, -size.height),
        (-size.width, 0pt),
        (-18pt, 0pt),
        (-8pt, 16pt),
        (-8pt, 0pt),
        (0pt, 0pt),
        (0pt, -size.height),
      ))
    }
  ]


  #let members = (
    location
      .subscriptions
      .fold((:), (acc, sub) => {
        let key = str(sub.member_no)
        let current = acc.at(key, default: (
          "first_name": sub.first_name,
          "last_name": sub.last_name.clusters().slice(0, 2).join("") + ".",
          "products": sub.products,
        ))
        acc.insert(key, current)
        return acc
      })
      .values()
      .sorted(by: (l, r) => {
        if l.last_name == r.last_name {
          return l.first_name < r.first_name
        }
        return l.last_name < r.last_name
      })
  )

  #show table.cell.where(y: 0): strong

  // #columns(2, balanced: true)[
  // needs https://github.com/typst/typst/pull/8207
  #table(
    columns: (1fr, auto, 1.5em),
    stroke: 0.3pt,
    fill: (x, y) => if calc.rem(y, 3) == 1 and y > 0 {
      gray.lighten(50%)
    },
    table.header("Vor- und Nachname (gekürzt)", "Anteile", sym.crossmark.heavy),
    ..for member in members {
      (
        strong(member.first_name) + " " + member.last_name,
        for product in member.products {
          (
            str(product.quantity) + sym.times + " " + product.name + "\n"
          )
        },
        "",
      )
    },
  )
  // ]

  #v(1fr)
  #set par(
    leading: 1.5em,
  )
  #grid(
    columns: (1fr, 1fr),
    [

      #sym.circle.stroked.big Wochenbladl verteilt\
      #sym.circle.stroked.big Kistenanzahl geprüft\
      #sym.circle.stroked.big Tauschkiste aufgestellt

    ],
    align(right + bottom)[

      #line(length: 15em)
      #emph[Unterschrift Fahrer·in]
    ],
  )


  // #context "" // needed for correct page counting when no content after table
  #label(location.name)
]
