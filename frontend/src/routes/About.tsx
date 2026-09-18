/**
 * `/about` — data provenance and methodology.
 *
 * Required by the project's own rules, and the page that makes the rest of the
 * product honest: where the boundaries come from, which complaints are real,
 * how the index is computed, and what we deliberately do not do.
 */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-line bg-surface p-5">
      <h2 className="text-base font-bold tracking-tight text-ink">{title}</h2>
      <div className="mt-2 space-y-2.5 text-sm leading-relaxed text-ink-2">{children}</div>
    </section>
  )
}

export default function About() {
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <header>
        <h1 className="text-xl font-bold tracking-tight text-ink">About this data</h1>
        <p className="mt-1 text-sm text-ink-2">
          What is real here, what is generated, and exactly how the Ward Neglect Index is computed.
        </p>
      </header>

      <Section title="The complaints on this deployment are demo data">
        <p>
          Every seeded report is flagged <code className="rounded bg-surface-2 px-1 font-mono text-xs">is_demo</code>{' '}
          in the database and labelled in the interface. They exist so the map and the leaderboard
          show a working product rather than an empty screen.
        </p>
        <p>
          Reports filed through this site are real and are <em>not</em> flagged as demo data.
        </p>
      </Section>

      <Section title="Ward boundaries are real, and are the pre-2022 delimitation">
        <p>
          Boundaries come from{' '}
          <a className="font-medium text-brand underline underline-offset-2" href="https://github.com/datameet/Municipal_Spatial_Data">
            DataMeet&rsquo;s Municipal Spatial Data
          </a>
          , licensed{' '}
          <a className="font-medium text-brand underline underline-offset-2" href="http://creativecommons.org/licenses/by-sa/2.5/in/">
            CC BY-SA 2.5 IN
          </a>
          , retrieved 19 September 2026. 289 wards: 272 MCD, 9 NDMC, 8 Delhi Cantonment Board.
        </p>
        <p>
          <strong className="text-ink">These are not the current boundaries.</strong> Delhi&rsquo;s
          three municipal corporations were unified in 2022 and re-delimited to 250 wards. We looked
          for the post-2022 boundaries as open data and could not find them published in a usable,
          openly-licensed form.
        </p>
        <p>
          We use this dataset because it is real, complete, correctly georeferenced and openly
          licensed, and we say what it is rather than implying it is current. That the present ward
          boundaries of a city of twenty million are not readily available as open data is itself a
          fair illustration of the problem this project is about.
        </p>
      </Section>

      <Section title="How the Ward Neglect Index is computed">
        <p>
          A score from 0 to 100 where <strong className="text-ink">higher is worse</strong>, built
          from three bounded parts against fixed anchors:
        </p>
        <ul className="ml-4 list-disc space-y-1">
          <li><strong className="text-ink">Backlog</strong> — what share of a ward&rsquo;s reports are still open.</li>
          <li><strong className="text-ink">Staleness</strong> — how long open reports have been waiting, capped at 90 days.</li>
          <li><strong className="text-ink">Sloth</strong> — how long past fixes took, capped at 60 days.</li>
        </ul>
        <p>
          Backlog and staleness carry 40% each and sloth 20%. Where a ward has never resolved
          anything there is no resolution speed to measure, so that weight is redistributed rather
          than scored as zero.
        </p>
        <p>
          <strong className="text-ink">A ward with fewer than five reports has no index at all</strong>,
          and shows &ldquo;not enough reports yet&rdquo;. Scoring a silent ward as zero would rank the
          wards nobody reports as the best-run wards in the city, which is precisely backwards.
        </p>
        <p>
          The anchors are fixed rather than relative to the city maximum, so a ward&rsquo;s score does
          not move because some other ward changed, and scores stay comparable over time.
        </p>
      </Section>

      <Section title="The index scores a ward, never a person">
        <p>
          The Neglect Index is computed partly from generated data. Attaching such a number to a
          real, named, elected individual would be indefensible, so the index belongs to the ward
          and is never presented as a person&rsquo;s score.
        </p>
        <p>
          Where councillor details appear they are identity only — name, party, and the source they
          came from — presented as public record and kept visually separate from the index. Anything
          we have not sourced renders as &ldquo;not available&rdquo;. We never guess.
        </p>
      </Section>

      <Section title="We do not email real officials">
        <p>
          Complaints are drafted and queued into a visible outbox, and delivered to a verified demo
          inbox. Sending unsolicited, AI-drafted mail to public servants from a demonstration
          system would be spam regardless of intent, so the live-sending path is switched off.
        </p>
      </Section>

      <Section title="Corrections">
        <p>
          If a boundary, a ward name or anything else here is wrong, please open an issue on{' '}
          <a className="font-medium text-brand underline underline-offset-2" href="https://github.com/amritkang165/meraward/issues">
            the project repository
          </a>
          . Boundary errors should also be reported upstream to DataMeet, so everyone benefits.
        </p>
      </Section>

      <p className="px-1 pb-2 text-xs leading-relaxed text-ink-3">
        Basemap © CARTO, © OpenStreetMap contributors. Ward boundaries © DataMeet contributors,
        CC BY-SA 2.5 IN — the derived boundary file in this project carries the same licence.
      </p>
    </div>
  )
}
