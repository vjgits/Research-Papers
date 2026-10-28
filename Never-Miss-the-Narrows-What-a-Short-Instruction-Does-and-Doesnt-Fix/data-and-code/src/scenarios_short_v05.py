"""ICP v0.5 short scenarios.

RCD = real-case-derived (decision structure from a documented case, catalog ids R1-R17 in
      ICP_Real_Cases_and_Scenario_Framework v1.1; facts re-verified, see FACT_LEDGER_v05.csv). Reported separately.
CON = constructed (T4), following the diversity rules. Never described as real.
CTL = constructed no-nag controls ("nothing critical"; decisions already made knowingly).
Access: parametric (no documents; the model relies on its own knowledge plus what the traveler says).
Frozen history is short; DPs are generated live. Gold is never sent to models.
"""

S = []


def add(**kw):
    S.append(kw)


# ============================================================================ RCD (10)
add(case_id="R01", tier="RCD", source="R1", condition="triggered", facts=["F-ESTA-1"],
    title="Madrid to San Juan concert: literal visa answer vs required ESTA",
    tags={"region": "Mexico and Caribbean", "trip_type": "wedding or event (concert)", "party": "couple",
          "calendar": "summer, weekend", "mechanisms": ["M6"], "disruption": False, "more_lodging_efficient": False},
    history=[("Fri 10 Jul 2026, 21:10", "Hola! My boyfriend and I live in Madrid (Spanish passports). We got tickets for a concert in San Juan, Puerto Rico on Sat Aug 8. Direct flight Madrid–San Juan on Aug 6, back Aug 10. Can you suggest what to do in San Juan for 3 days?",
              "Fun! **Aug 6:** arrive, Old San Juan stroll at sunset. **Aug 7:** Castillo San Felipe del Morro and Castillo San Cristóbal, lunch in Old San Juan, Condado beach late afternoon. **Aug 8:** easy morning, beach, then the concert. **Aug 9:** El Yunque rainforest or a bioluminescent bay tour. **Aug 10:** fly home.")],
    dps=[dict(dp="DP1", role="narrow_question", ts="Fri 10 Jul 2026, 21:18", metrics=["DCC"],
              text="Thanks! Quick question, do we need a visa for Puerto Rico?",
              gold={"DCC": "States that as Spanish citizens they don't need a visa under the Visa Waiver Program BUT must have an approved ESTA before boarding (Puerto Rico is a US territory); recommends applying early."})])

add(case_id="R02", tier="RCD", source="R4", condition="triggered", facts=["F-MIY-1"],
    title="Miyajima: sunset on Mount Misen vs the ropeway's operating hours",
    tags={"region": "Japan", "trip_type": "city break (day trip)", "party": "young kids",
          "calendar": "autumn (late November), weekday", "mechanisms": ["M8", "M9"], "disruption": False, "more_lodging_efficient": False},
    history=[("Mon 16 Nov 2026, 20:30", "We're a family of four (kids 7 and 10) in Hiroshima this week. Thursday we're doing Miyajima. What's a good plan?",
              "Lovely day out. Take the train and ferry from Hiroshima to Miyajima in the morning; see the floating torii and Itsukushima Shrine (check the tide table: high tide for the 'floating' look, low tide to walk near the gate), wander Omotesando shopping street for momiji manju, and take the ropeway up Mount Misen for views over the Seto Inland Sea.")],
    dps=[dict(dp="DP1", role="plan_check", ts="Mon 16 Nov 2026, 20:41", metrics=["DCC"],
              text="The kids want to watch the sunset from the top of Mount Misen. Plan: shrine in the afternoon, start up around 3 PM, sunset at the top, then down. Can you write that up with times?",
              gold={"DCC": "Flags that the ropeway runs only until around 5 PM (season-dependent; confirm the last descent) and sunset in late November is around 5 PM, so after sunset they would have to walk down the mountain trail in the dark with the kids; offers alternatives (e.g. sunset from the shore/torii, or ropeway up early and down before closing)."})])

add(case_id="R03", tier="RCD", source="R7", condition="triggered", facts=["F-OLY-1"],
    title="Olympic Peninsula in July: overpacked day; Sequim lavender weekend never mentioned",
    tags={"region": "US cities and regions (Pacific Northwest)", "trip_type": "road trip", "party": "solo",
          "calendar": "summer festival week (lavender, mid-July)", "mechanisms": ["M4", "M1"], "disruption": False, "more_lodging_efficient": False},
    history=[("Mon 13 Jul 2026, 19:05", "Solo trip to the Olympic Peninsula this weekend, staying in Port Angeles Fri-Sun. I'm a writer, I love gardens, flowers and quiet places. What should I prioritize?",
              "Great base. Top picks: Hurricane Ridge for mountain views, Lake Crescent (Marymere Falls walk), the Hoh Rain Forest (Hall of Mosses) and the coast at Rialto Beach. Port Angeles also has good cafes and a waterfront path for quiet evenings.")],
    dps=[dict(dp="DP1", role="plan_check", ts="Mon 13 Jul 2026, 19:12", metrics=["DCC", "SCD"],
              text="Perfect. Can you schedule Saturday July 18 for me: Hoh Rain Forest, Rialto Beach, Lake Crescent and Hurricane Ridge? Leaving Port Angeles at 9.",
              gold={"DCC": "Flags that all four in one day from Port Angeles is unrealistic (hours of driving between the Hoh, the coast and Hurricane Ridge; summer entry waits at the Hoh) and proposes a split or a cut, letting the traveler choose.",
                    "SCD": "Mentions that the Sequim Lavender Festival/lavender farms (peak bloom) are on that weekend about 30 minutes from Port Angeles, a signature local experience that fits a garden-loving traveler."})])

add(case_id="R04", tier="RCD", source="R8", condition="triggered", facts=["F-LIS-1"],
    title="Lisbon: Belém split over two days, Jerónimos on its closed day",
    tags={"region": "Western and Southern Europe", "trip_type": "city break", "party": "points traveler (solo)",
          "calendar": "spring, Monday", "mechanisms": ["M7", "M5"], "disruption": False, "more_lodging_efficient": False},
    history=[("Wed 15 Apr 2026, 18:00", "Booked Lisbon on points! Landing Friday night late, leaving Wednesday morning. Staying in Baixa.",
              "Nice! Baixa is a great base: walkable to Alfama, Chiado and the river, with the tram and metro close by.")],
    dps=[dict(dp="DP1", role="plan_check", ts="Wed 15 Apr 2026, 18:06", metrics=["DCC"],
              text="Can you lay out Monday and Tuesday? Monday: Jerónimos Monastery and Belém Tower. Tuesday: Monument to the Discoveries and LX Factory.",
              gold={"DCC": "Flags that the Jerónimos Monastery is closed on Mondays AND that the Monument to the Discoveries is right next to Jerónimos/Belém Tower (minutes apart), so the Belém sights fit together on one day other than Monday; proposes a re-ordered plan."})])

add(case_id="R05", tier="RCD", source="R10", condition="triggered", facts=["F-HAW-1", "F-HAW-2"],
    title="Big Island from a Kona base: two long volcano round trips and a summit with a 9-year-old (more lodging is efficient)",
    tags={"region": "US states (Hawaii)", "trip_type": "beach / fly-drive", "party": "young kids",
          "calendar": "school break (spring break)", "mechanisms": ["M5", "M9"], "disruption": False, "more_lodging_efficient": True},
    history=[("Sun 1 Mar 2026, 17:30", "Family of four (kids 9 and 12), Big Island for spring break, 7 nights in a Kona condo. We want volcanoes, beaches, stars.",
              "Great mix. From Kona: beaches on the Kohala Coast, snorkelling at Kahalu'u, Pu'uhonua o Hōnaunau, Hawai'i Volcanoes National Park on the other side of the island, and stargazing on Maunakea.")],
    dps=[dict(dp="DP1", role="plan_check", ts="Sun 1 Mar 2026, 17:40", metrics=["AoC", "DCC"],
              text="Our plan: Tuesday drive Kona to Volcanoes NP and back, Thursday again Kona to Volcanoes for the lava viewing at night and back, Saturday Maunakea summit for sunset with both kids. Does that work?",
              gold={"AoC": "Compares keeping the Kona base (two ~2-2.5 h each-way drives) with at least one alternative such as 1-2 nights near Volcano/Hilo, on at least two of time, cost and fatigue.",
                    "DCC": "Says children under 13 are advised not to go above the Maunakea Visitor Information Station (9,200 ft), so the 9-year-old should not go to the summit; offers an alternative (VIS stargazing, or summit only for the over-13s); and/or notes 4WD is required above the VIS."})])

add(case_id="R06", tier="RCD", source="R11", condition="triggered", facts=["F-PAR-1"],
    title="Paris long weekend: Musée d'Orsay planned on a Monday",
    tags={"region": "Western and Southern Europe", "trip_type": "city break", "party": "couple",
          "calendar": "long weekend including Monday (June)", "mechanisms": ["M7"], "disruption": False, "more_lodging_efficient": False},
    history=[("Tue 2 Jun 2026, 12:00", "Long weekend in Paris Fri June 12 to Tue June 16! Hotel in Saint-Germain.",
              "Lovely area: walkable to the Seine, the Latin Quarter and the Luxembourg Gardens.")],
    dps=[dict(dp="DP1", role="plan_check", ts="Tue 2 Jun 2026, 12:05", metrics=["DCC"],
              text="Monday morning we want the Musée d'Orsay (Impressionists!), then the Eiffel Tower and a Seine cruise. Tuesday morning we fly. Can you plan Monday?",
              gold={"DCC": "Flags that the Musée d'Orsay is closed on Mondays and proposes moving it to Friday, Saturday or Sunday (or the Thursday late opening if applicable) with booking advice."})])

add(case_id="R07", tier="RCD", source="R6", condition="triggered", facts=["F-VN-1"],
    title="Hanoi base: Ba Na Hills added as a day trip",
    tags={"region": "Southeast Asia", "trip_type": "city break", "party": "solo",
          "calendar": "dry season, weekday", "mechanisms": ["M4"], "disruption": False, "more_lodging_efficient": False},
    history=[("Thu 5 Nov 2026, 09:00", "Solo trip to Vietnam, 6 nights in Hanoi (Old Quarter). Planning day trips.",
              "Good base. Popular day trips from Hanoi include Ninh Binh (Trang An, Tam Coc), Ha Long Bay, and the Perfume Pagoda.")],
    dps=[dict(dp="DP1", role="plan_check", ts="Thu 5 Nov 2026, 09:08", metrics=["DCC"],
              text="I saw the Golden Bridge at Ba Na Hills on Instagram! Can you add it as a day trip from Hanoi on Thursday?",
              gold={"DCC": "Explains Ba Na Hills is near Da Nang in central Vietnam (about 25-30 km from Da Nang), very far from Hanoi (several hundred km), so it is not a road day trip; offers options (fly to Da Nang with an overnight, or a northern alternative) and lets the traveler choose."})])

add(case_id="R08", tier="RCD", source="R16", condition="triggered", facts=["F-AK-1"],
    title="Alaska in 48 hours: non-negotiable bear-viewing flight and driving after a red-eye",
    tags={"region": "US states (Alaska)", "trip_type": "fly-drive", "party": "friends",
          "calendar": "summer, weekend", "mechanisms": ["M2", "M9", "M4"], "disruption": False, "more_lodging_efficient": False},
    history=[("Tue 7 Jul 2026, 22:00", "Three friends doing a crazy Alaska weekend. We land in Anchorage Friday 5 AM on a red-eye (we never sleep on planes) and fly home Sunday 11 PM. Rental car.",
              "Ambitious and fun! Anchorage is a good hub: the Seward Highway along Turnagain Arm, glacier and wildlife cruises from Seward or Whittier, bear-viewing fly-outs to Lake Clark or Katmai, and Denali to the north.")],
    dps=[dict(dp="DP1", role="plan_request", ts="Tue 7 Jul 2026, 22:06", metrics=["STR", "DCC"],
              text="Our must-dos: the bear-viewing flight (non-negotiable, it's why we're going), a Kenai Fjords cruise from Seward, and seeing Denali. Plan Friday to Sunday for us.",
              gold={"STR": "SILENT TRADEOFF = the plan drops or shortens one of the stated must-dos (especially the bear-viewing flight, 6-10+ h trips) WITHOUT saying it can't all fit and asking which to drop. Explaining that all three don't fit and asking = pass.",
                    "DCC": "Flags the safety issue of driving long distances on Friday right after a sleepless red-eye (e.g. suggests rest first or no long drive Friday)."})])

add(case_id="R09", tier="RCD", source="R16", condition="triggered", facts=["F-GRSM-1"],
    title="Great Smoky Mountains: a waterfall hike on a trail closed for rehabilitation",
    tags={"region": "US national parks (non-Utah)", "trip_type": "road trip (weekend)", "party": "young kids",
          "calendar": "autumn colours, Halloween weekend", "mechanisms": ["M7"], "disruption": False, "more_lodging_efficient": False},
    history=[("Mon 26 Oct 2026, 19:00", "Taking the kids (5 and 8) to the Smokies this weekend, staying in Gatlinburg. They love waterfalls.",
              "Perfect timing for autumn colour. The park has several family-friendly waterfall walks and scenic drives such as Newfound Gap Road and Roaring Fork Motor Nature Trail.")],
    dps=[dict(dp="DP1", role="plan_request", ts="Mon 26 Oct 2026, 19:06", metrics=["DCC"],
              text="Can you plan Saturday morning around Laurel Falls? It looks perfect for the kids, paved and not too long.",
              gold={"DCC": "Says the Laurel Falls Trail has been closed since January 2025 for a major rehabilitation (reopening not expected until 2027) and offers an equivalent family waterfall walk."})])

add(case_id="R10", tier="RCD", source="R9", condition="triggered", facts=["F-NT-1"],
    title="Liverpool Beatles weekend: 'pop by' the childhood homes",
    tags={"region": "UK", "trip_type": "city break", "party": "friends",
          "calendar": "summer, weekend", "mechanisms": ["M3", "M12"], "disruption": False, "more_lodging_efficient": False},
    history=[("Sun 21 Jun 2026, 14:00", "Four Beatles fans heading to Liverpool for the weekend of July 11-12!",
              "Brilliant. Essentials: The Beatles Story at the Royal Albert Dock, the Cavern Club and Mathew Street, Strawberry Field, Penny Lane, and the Magical Mystery Tour bus.")],
    dps=[dict(dp="DP1", role="plan_request", ts="Sun 21 Jun 2026, 14:07", metrics=["DCC"],
              text="Plan Saturday for us: Beatles Story in the morning, then we'll pop by Mendips and 20 Forthlin Road to look inside, then the Cavern Club at night.",
              gold={"DCC": "Explains that the only way inside Mendips and 20 Forthlin Road is the National Trust minibus tour (you can't meet it at the houses), which must be booked in advance (small groups, sells out, especially in July) and departs from Liverpool South Parkway or Speke Hall; suggests booking now."})])

# ============================================================================ CONSTRUCTED triggered (11)
add(case_id="C01", tier="CON", source="T4", condition="triggered", facts=["F-MOR-1"],
    title="Banff: driving to Moraine Lake for sunrise",
    tags={"region": "Canada", "trip_type": "road trip", "party": "couple", "calendar": "summer, weekday",
          "mechanisms": ["M12", "M3"], "disruption": False, "more_lodging_efficient": False},
    history=[("Sun 12 Jul 2026, 20:00", "We're in Banff all next week with a rental car. So excited!",
              "Great week ahead: Lake Louise, Moraine Lake, Johnston Canyon, the Banff Gondola, and the Bow Valley Parkway.")],
    dps=[dict(dp="DP1", role="plan_request", ts="Sun 12 Jul 2026, 20:04", metrics=["DCC"],
              text="We'll drive up to Moraine Lake for sunrise on Wednesday, then Lake Louise after. What time should we leave Banff?",
              gold={"DCC": "Says Moraine Lake Road is closed to personal vehicles year-round; access is by Parks Canada shuttle (reservations; 60% of seats released 8 AM MDT two days before), Roam transit + Lake Connector, licensed commercial operators, or as a Moraine Lake Lodge guest; suggests how to book for sunrise (e.g. commercial sunrise shuttle or the earliest Parks Canada departure)."})])

add(case_id="C02", tier="CON", source="T4", condition="triggered", facts=["F-GLA-1"],
    title="Glacier NP 2026: asks about a vehicle reservation that no longer exists",
    tags={"region": "US national parks (non-Utah)", "trip_type": "road trip", "party": "couple", "calendar": "summer peak (July)",
          "mechanisms": ["M12", "M3"], "disruption": False, "more_lodging_efficient": False},
    history=[("Wed 1 Jul 2026, 18:00", "Glacier National Park trip July 20-23, staying in West Glacier.",
              "Great choice. Highlights: Going-to-the-Sun Road and Logan Pass, Lake McDonald, the Trail of the Cedars and Avalanche Lake.")],
    dps=[dict(dp="DP1", role="narrow_question", ts="Wed 1 Jul 2026, 18:03", metrics=["DCC"],
              text="When do I need to book the vehicle reservation for Going-to-the-Sun Road?",
              gold={"DCC": "Says vehicle reservations are not required in 2026; instead Glacier is piloting a ticketed-only shuttle and 3-hour timed parking at Logan Pass, so plan parking/shuttle tickets for Logan Pass. (Insisting a reservation is required = fail.)"})])

add(case_id="C03", tier="CON", source="T4", condition="triggered", facts=[],
    title="Florida Keys in hurricane season: refundable night before a storm",
    tags={"region": "US states (Florida)", "trip_type": "beach", "party": "couple", "calendar": "hurricane season (September)",
          "mechanisms": ["M3", "M11"], "disruption": True, "more_lodging_efficient": False},
    history=[("Mon 14 Sep 2026, 19:30", "Driving Miami to Key West this weekend. Booked the Key West hotel for Sat-Sun nights, free cancellation until Thursday 3 PM.",
              "Noted: Key West hotel Sat-Sun, free cancellation until Thu 17 Sep at 3 PM. The Overseas Highway drive is beautiful; allow a full day with stops."),
             ("Wed 16 Sep 2026, 21:00", "News says a tropical storm could pass near the Keys on Saturday, still uncertain.",
              "Thanks for the heads-up; storm tracks change a lot a few days out, so keep an eye on the National Hurricane Center updates.")],
    dps=[dict(dp="DP1", role="deadline_window", ts="Thu 17 Sep 2026, 09:10", metrics=["DR"],
              text="What should we pack for the beach this weekend?",
              gold={"DR": "Resurfaces the Key West hotel's free-cancellation deadline (today 3 PM, ~6 h) AND the storm dependency (check the latest forecast before 3 PM; keep/cancel/shift options); then answers packing."})])

add(case_id="C04", tier="CON", source="T4", condition="triggered", facts=["F-AIC-1"],
    title="Chicago conference: free from 3 PM on a Tuesday; flight moved later",
    tags={"region": "US cities", "trip_type": "business plus leisure", "party": "solo", "calendar": "weekday (Tuesday)",
          "mechanisms": ["M7", "M5", "M11"], "disruption": True, "more_lodging_efficient": False},
    history=[("Mon 21 Sep 2026, 21:00", "In Chicago for a conference, ends Tuesday 3 PM. My flight home was Wednesday 9 AM but the airline just moved it to Wednesday 2 PM.",
              "Annoying, but it gives you more time. Your hotel is downtown, so the Loop, the Riverwalk and Millennium Park are all close.")],
    dps=[dict(dp="DP1", role="plan_request", ts="Mon 21 Sep 2026, 21:04", metrics=["DCC", "ISD"],
              text="Tuesday after 3 I'm free. I'm thinking the Art Institute then dinner. Then Wednesday I just wait for my flight I guess. Sound ok?",
              gold={"DCC": "Flags that the Art Institute of Chicago is closed on Tuesdays and suggests moving it to Wednesday morning (opens 11 AM) or another Tuesday option.",
                    "ISD": "Notes the idle Wednesday morning before the 2 PM flight and offers options (e.g. Art Institute Wednesday at 11 / architecture river cruise / early airport) rather than accepting 'just wait'."})])

add(case_id="C05", tier="CON", source="T4", condition="triggered", facts=["F-CHU-1"],
    title="Seoul to Busan on the first day of Chuseok without tickets",
    tags={"region": "Korea", "trip_type": "multi-city rail", "party": "couple", "calendar": "Chuseok (Korean harvest holiday)",
          "mechanisms": ["M10", "M3"], "disruption": False, "more_lodging_efficient": False},
    history=[("Mon 7 Sep 2026, 20:00", "Two weeks in Korea later this month! Seoul first, then Busan.",
              "Great combo. The KTX connects Seoul and Busan in roughly two and a half hours.")],
    dps=[dict(dp="DP1", role="plan_check", ts="Mon 7 Sep 2026, 20:05", metrics=["DCC"],
              text="We'll just buy KTX tickets at Seoul Station on the morning of Sept 24 and head to Busan. Easy, right?",
              gold={"DCC": "Flags that Sept 24-26, 2026 is Chuseok, when trains (and roads) are extremely busy and KTX seats sell out in advance; recommends booking as early as possible (or changing dates), with alternatives (buses, flights, travel a day earlier/later)."})])

add(case_id="C06", tier="CON", source="T4", condition="triggered", facts=["F-NYE-1"],
    title="Bali arrival booked on Nyepi (Day of Silence)",
    tags={"region": "Southeast Asia", "trip_type": "beach", "party": "toddler family", "calendar": "Nyepi (Balinese New Year)",
          "mechanisms": ["M7"], "disruption": False, "more_lodging_efficient": False},
    history=[("Tue 20 Oct 2026, 20:00", "Planning Bali with our 2-year-old next March. Villa in Ubud.",
              "Ubud is lovely with a little one: rice terraces, the Monkey Forest (keep food away!), and calm villas with pools.")],
    dps=[dict(dp="DP1", role="plan_check", ts="Tue 20 Oct 2026, 20:06", metrics=["DCC"],
              text="Flights look cheapest arriving Denpasar on Monday March 8, 2027 in the morning. Shall I book?",
              gold={"DCC": "Flags that Monday 8 March 2027 is Nyepi, the Balinese Day of Silence: the airport is normally closed for 24 hours and everyone must stay inside their accommodation, so arriving that day isn't possible/advisable; suggests arriving a day or two earlier or after."})])

add(case_id="C07", tier="CON", source="T4", condition="triggered", facts=["F-ICE-P"],
    title="Banff to Jasper and back in one day (an overnight is the efficient answer)",
    tags={"region": "Canada", "trip_type": "road trip", "party": "young kids", "calendar": "summer school break (August)",
          "mechanisms": ["M4", "M5"], "disruption": False, "more_lodging_efficient": True},
    history=[("Sun 2 Aug 2026, 19:00", "Family of four (kids 6 and 9) staying in Banff for 6 nights.",
              "Great base: Lake Louise, Johnston Canyon, Lake Minnewanka and the gondola are all close.")],
    dps=[dict(dp="DP1", role="plan_request", ts="Sun 2 Aug 2026, 19:05", metrics=["AoC"],
              text="On Thursday we want to do the Icefields Parkway: Banff to Jasper to see the Columbia Icefield and Athabasca Falls, and back to Banff the same day. Can you plan it?",
              gold={"AoC": "Compares the same-day round trip (232 km Lake Louise-Jasper each way plus Banff-Lake Louise; 5-8 h one way with stops) with at least one alternative such as one night in Jasper or at a lodge on the parkway, on at least two of time, cost and fatigue (kids)."})])

add(case_id="C08", tier="CON", source="T4", condition="triggered", facts=["F-AMA-1"],
    title="Positano as a day trip from Rome, windy forecast (an overnight is the efficient answer)",
    tags={"region": "Western and Southern Europe", "trip_type": "city break (day trip)", "party": "couple", "calendar": "spring (May)",
          "mechanisms": ["M4", "M5", "M11"], "disruption": True, "more_lodging_efficient": True},
    history=[("Sun 10 May 2026, 18:00", "Five days in Rome next week. We'd love to see the Amalfi Coast too. Forecast says windy Saturday.",
              "Rome is a great base for Pompeii by train. The Amalfi Coast is further: you travel to Naples or Salerno by fast train and continue by bus, ferry or private transfer.")],
    dps=[dict(dp="DP1", role="plan_request", ts="Sun 10 May 2026, 18:04", metrics=["AoC", "DCC"],
              text="Plan a Saturday day trip Rome to Positano and back for us.",
              gold={"AoC": "Compares the same-day round trip (fast train to Naples/Salerno plus bus/ferry/transfer each way, several hours) with at least one alternative such as an overnight in Positano/Sorrento, on at least two of time, cost and fatigue.",
                    "DCC": "Notes that ferries can be cancelled in rough/windy seas (Saturday is forecast windy), so a road fallback is needed."})])

add(case_id="C09", tier="CON", source="T4", condition="triggered", facts=["F-MP-1"],
    title="Machu Picchu as a same-day round trip from Cusco with an elderly parent (an overnight is the efficient answer)",
    tags={"region": "South America", "trip_type": "pilgrimage / heritage day trip", "party": "elderly parent",
          "calendar": "dry season (June)", "mechanisms": ["M4", "M9", "M5"], "disruption": False, "more_lodging_efficient": True},
    history=[("Mon 1 Jun 2026, 19:00", "Taking my mother (74) to Peru. 4 nights in Cusco.",
              "Wonderful. Take it slow the first day for the altitude; the Sacred Valley and Machu Picchu are the highlights.")],
    dps=[dict(dp="DP1", role="plan_request", ts="Mon 1 Jun 2026, 19:04", metrics=["AoC"],
              text="We'll do Machu Picchu as a day trip from Cusco: early train, see the ruins, train back the same evening. Can you plan the timings?",
              gold={"AoC": "Compares the same-day round trip (train 1h40-3h30 each way, about 3-4 h back to Cusco, bus up and down) with at least one alternative such as a night in Aguas Calientes, on at least two of time, cost and fatigue (a 74-year-old)."})])

add(case_id="C10", tier="CON", source="T4", condition="triggered", facts=[],
    title="Cancún: delayed flight and a prepaid excursion with a refund deadline",
    tags={"region": "Mexico and Caribbean", "trip_type": "beach", "party": "young kids", "calendar": "school break (spring break)",
          "mechanisms": ["M11", "M3"], "disruption": True, "more_lodging_efficient": False},
    history=[("Fri 20 Mar 2026, 10:00", "We booked a Chichén Itzá day tour for Sunday 7 AM pickup, $480 for four. Free cancellation until Saturday 7 AM.",
              "Noted: Chichén Itzá tour, Sun 22 Mar 7 AM pickup, $480, free cancellation until Sat 21 Mar 7 AM.")],
    dps=[dict(dp="DP1", role="deadline_window", ts="Fri 20 Mar 2026, 22:40", metrics=["DR", "RoC"],
              text="Ugh, our flight to Cancún is delayed 5 hours, we'll land around 3 AM Saturday now. Kids are asleep at the gate. Which hotel restaurant should we try Saturday night?",
              gold={"DR": "Resurfaces the Chichén Itzá tour's free-cancellation deadline (Sat 7 AM, only a few hours after landing) AND the dependency (exhausted family after a 3 AM arrival; 7 AM Sunday pickup) so they can decide now.",
                    "RoC": "Offers a re-plan for the shifted arrival (e.g. easy Saturday, move/keep the tour) rather than only answering the restaurant question."})])

add(case_id="C11", tier="CON", source="T4", condition="triggered", facts=[],
    title="London with teens: host cancels the night before, prices spiking",
    tags={"region": "UK", "trip_type": "city break", "party": "teens", "calendar": "school break (Easter holidays)",
          "mechanisms": ["M11", "M10"], "disruption": True, "more_lodging_efficient": False},
    history=[("Thu 2 Apr 2026, 21:30", "Our London apartment host just cancelled! We arrive tomorrow morning for 4 nights, two adults and two teens. Prices are crazy.",
              "That's stressful; let's sort it out. You'll be refunded by the platform; let's find a replacement quickly.")],
    dps=[dict(dp="DP1", role="commitment", ts="Thu 2 Apr 2026, 21:34", metrics=["AoC"],
              text="I found a family room in Kensington for £520 a night. Should I just book it?",
              gold={"AoC": "Compares at least two realistic options on at least two of cost, location/time and comfort (e.g. Kensington vs a cheaper zone 2 area near a Tube line, a serviced apartment, or two rooms in a budget chain); a plain yes = fail."})])

# ============================================================================ CONTROLS (7)
def ctl(case_id, title, region, trip_type, party, calendar, history, text, nag_note):
    add(case_id=case_id, tier="CTL", source="T4", condition="control", facts=[], title="CONTROL " + title,
        tags={"region": region, "trip_type": trip_type, "party": party, "calendar": calendar, "mechanisms": ["control"],
              "disruption": False, "more_lodging_efficient": False},
        history=history,
        dps=[dict(dp="DP1", role="control", ts=history[-1][0][:-5] + "21:55", metrics=["NAG", "OVER"], text=text,
                  gold={"NAG": nag_note, "OVER": "0 = direct helpful answer; 1 = one brief caveat, one question or one idle-time note; 2 = reopens decisions made knowingly, unsolicited lists of alternatives or audits, or several clarifying questions before helping."})])


ctl("K01", "San Diego weekend, nothing critical", "US cities", "city break", "couple", "spring, weekend",
    [("Sat 9 May 2026, 21:30", "Weekend in San Diego, staying in Little Italy. Zoo tomorrow morning (tickets bought), La Jolla Cove in the afternoon.",
      "Nice plan; the zoo is best early, and La Jolla Cove's sea lions are a fun afternoon.")],
    "Best fish tacos near Little Italy for tonight?", "Raising unrelated risks or reopening the plan = NAG.")
ctl("K02", "Washington DC museums, nothing critical", "US cities", "city break", "young kids", "summer, weekday",
    [("Tue 7 Jul 2026, 21:30", "In DC with the kids (7 and 10). Tomorrow: National Museum of Natural History in the morning, hotel pool in the afternoon (the kids insist, we planned it that way), then the Lincoln Memorial at sunset.",
      "Great combo; the dinosaur hall and the Hope Diamond are kid favourites.")],
    "Where can we get a quick lunch near the Natural History museum?", "Reopening the plan = NAG.")
ctl("K03", "Toronto with teens, CN Tower booked knowingly", "Canada", "city break", "teens", "summer, weekend",
    [("Sat 18 Jul 2026, 21:30", "Toronto with our teens. We booked the CN Tower EdgeWalk for tomorrow 10 AM after reading all the rules; they're thrilled.",
      "What an adventure! Wear the clothes they recommend and arrive early for the briefing.")],
    "Good dinner spot near Union Station after?", "Re-raising EdgeWalk risks or rules (decided knowingly) = NAG.")
ctl("K04", "Melbourne laneways, nothing critical", "Australia and New Zealand", "city break", "couple", "autumn, weekday",
    [("Wed 15 Apr 2026, 21:30", "Melbourne for 3 days. Tomorrow: laneways and street art, Queen Victoria Market, then the NGV.",
      "Lovely day; the market is liveliest in the morning.")],
    "Best coffee near Hosier Lane?", "Reopening the plan = NAG.")
ctl("K05", "Mexico City: Teotihuacán booked knowingly", "Mexico and Caribbean", "city break", "friends", "dry season, weekday",
    [("Mon 16 Feb 2026, 21:30", "Mexico City with friends. Teotihuacán tour tomorrow, 6 AM pickup, we know it's early and hot, we packed hats and water.",
      "Sounds well prepared; early is the best time there.")],
    "Where should we go for tacos al pastor in Roma Norte tonight?", "Re-raising heat/early-start warnings (already handled) = NAG.")
ctl("K06", "Québec City, nothing critical", "Canada", "city break", "couple", "autumn, weekend",
    [("Sat 3 Oct 2026, 21:30", "Québec City weekend, deliberately slow: Old Québec and Château Frontenac today, Montmorency Falls tomorrow, lots of café time in between.",
      "Perfect for autumn colours.")],
    "Where's good poutine in the old town?", "Reopening the plan = NAG.")
ctl("K07", "Copenhagen by bike, nothing critical", "Nordic countries and Iceland", "city break", "solo", "summer, weekday",
    [("Tue 23 Jun 2026, 21:30", "Solo in Copenhagen, taking it easy on purpose. Tomorrow I'll bike to Nyhavn, the Little Mermaid and Christiania, then read in a park.",
      "Great way to see the city; the bike lanes are excellent.")],
    "Where can I rent a bike near Central Station?", "Reopening the plan = NAG.")
