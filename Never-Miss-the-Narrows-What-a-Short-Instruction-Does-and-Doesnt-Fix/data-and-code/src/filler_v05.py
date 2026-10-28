"""Filler exchanges for the frozen middle of long-horizon (LH) conversations.

Each family yields (user, assistant) pairs from per-case slots. The text is deliberately ordinary trip chatter: it never
mentions the case's signature (★) item, its bookings or deadlines (the validator enforces this), so that the only
disclosures of those come from the hand-written anchor turns. Phase "pre" = before the trip, "trip" = during the trip.
Template-generated filler is a stated threat to realism (docs/PREREGISTRATION_v05.md, threats).
"""
import random

def _fams():
    F = []

    def fam(phase, parties=("any",)):
        def deco(fn):
            F.append((phase, parties, fn))
            return fn
        return deco

    @fam("pre")
    def packing_layers(s, r):
        m = s["month"]
        return [(f"What clothes should we pack for {s['region']} in {m}?",
                 f"For {s['region']} in {m}, pack layers rather than one heavy coat: a base layer, a fleece or light down jacket, "
                 f"and a waterproof shell. Days can feel very different from mornings and evenings, so plan to add and remove layers. "
                 f"Comfortable walking shoes with grip matter more than anything else; bring a spare pair of socks in the day bag. "
                 f"A hat, sunglasses and sunscreen are worth packing even if the forecast looks cool.")]

    @fam("pre")
    def packing_daybag(s, r):
        return [("What should go in our day bag every day?",
                 "A simple day-bag list: refillable water bottles, snacks, sunscreen, a light rain layer, a small first-aid kit "
                 "(plasters, pain relief, any personal medication), phone power bank and cable, a printed or offline copy of "
                 "bookings, and a little cash. " + ("Wet wipes and a change of clothes for the kids save a lot of stress. " if s["kids"] else "")
                 + "Keep it light so whoever carries it isn't worn out by mid-afternoon.")]

    @fam("pre")
    def phone_data(s, r):
        return [("Will our phones work there or should we get something?",
                 f"Coverage around {s['region']} is good in towns but can be patchy on the road between them. Two cheap safeguards: "
                 f"download offline maps for the whole area before you leave, and save your bookings as screenshots or PDFs. "
                 + (f"Check whether your plan includes roaming in {s['country']}; if not, an eSIM bought before departure is usually the cheapest option. "
                    if s.get("international") else "")
                 + "A car charger and a power bank cover long days.")]

    @fam("pre")
    def money(s, r):
        return [("Cash or cards?",
                 f"Cards are accepted almost everywhere in {s['country']}, including small cafes, and contactless is common. "
                 f"Keep a small amount of cash for the odd market stall, parking machine or tip. Tell your bank you are travelling so "
                 f"a fraud check doesn't block your card on day one, and carry a second card in a different bag.")]

    @fam("pre")
    def home_prep(s, r):
        return [("Anything we should sort out at home before we leave?",
                 "A short checklist: pause or redirect deliveries, set lights on a timer, arrange plant watering, check that "
                 "passports/IDs and driving licences are valid, confirm the car rental and any parking at the airport, and charge "
                 "every device the night before. Putting copies of your documents in a shared cloud folder helps if something gets lost.")]

    @fam("pre")
    def rental_car(s, r):
        if s["transport"] != "car":
            return []
        return [("Anything to know about the rental car?",
                 "At pickup, photograph the car all round and the fuel gauge, check the spare tyre and that you have the documents "
                 "the company requires. Ask what fuel it takes and whether there are mileage limits. Credit-card rental cover "
                 "varies, so check what yours includes before you decline the counter insurance. Fill up whenever you're under half "
                 "a tank on rural stretches.")]

    @fam("pre", ("kids",))
    def car_entertainment(s, r):
        return [("Any ideas to keep the kids happy on the long drives?",
                 "A few that work well: an audiobook series everyone likes, a 'spot the animal' or licence-plate game, a snack "
                 "bag they can only open at set stops, and a stop every 90 minutes or so to run around. Downloading shows in "
                 "advance avoids relying on signal. Giving each child a small 'job' (navigator, DJ, snack manager) helps too.")]

    @fam("pre", ("elder",))
    def elder_comfort(s, r):
        return [(f"{s['elder_name']} gets stiff sitting for a long time. Any tips?",
                 "Plan a short stop every hour to 90 minutes to stand and walk a little, choose a front seat with good legroom, "
                 "and keep water and a small cushion within reach. Schedule the longest drives for the morning when energy is "
                 "higher. Supportive shoes and a light folding stool can make "
                 "viewpoint stops more comfortable.")]

    @fam("pre")
    def budget(s, r):
        return [("Roughly what should we budget per day for food?",
                 f"In {s['region']}, a sensible plan is a simple breakfast where you stay, a casual lunch or picnic, and one sit-down "
                 f"dinner. Groceries for picnics save a lot in tourist areas, where restaurant prices are higher. Set a daily food "
                 f"budget per person, check it each evening, and allow a little extra for treats and coffee stops.")]

    @fam("pre")
    def photo_gear(s, r):
        return [("Should I bring my camera or is the phone enough?",
                 "A recent phone is enough for most travel photos, especially for wide scenery. A camera with a zoom lens helps "
                 "for wildlife and distant details. Whatever you bring, a spare battery or power bank and enough storage matter "
                 "more than extra lenses. Soft early-morning and late-afternoon light gives the best results.")]

    @fam("pre")
    def insurance(s, r):
        return [("Do we need travel insurance?",
                 "It's worth it for medical cover and for trip interruption. Check what your credit card already includes, then "
                 "look for a policy that covers medical treatment, evacuation if relevant, cancellations for illness, and lost "
                 "luggage. Keep the policy number and emergency phone number in your phone and on paper.")]

    @fam("pre")
    def minor_sight(s, r):
        out = []
        for name, blurb in s["minor_sights"]:
            out.append((f"Is {name} worth a stop?",
                        f"{name}: {blurb} It's a pleasant stop if it fits naturally into your route, but not something to build a "
                        f"day around."))
        return out

    @fam("pre")
    def food_try(s, r):
        out = []
        for dish in s["foods"]:
            out.append((f"Is {dish} something we should try?",
                        f"Yes, {dish} is a good local thing to try. Ask at your lodging where locals go for it; small family-run "
                        f"places are often better than the busiest spots. If anyone has dietary restrictions, ask how it's made."))
        return out

    @fam("pre")
    def flight_seat(s, r):
        if not s.get("flies"):
            return []
        return [("Any tips for the flights?",
                 "Check in online as soon as it opens, keep medication, chargers and a change of clothes in the carry-on, and "
                 "photograph your checked bags in case they go missing. Drink water, walk around on longer flights, and set your "
                 "watch to local time once you board to help with jet lag.")]

    @fam("pre")
    def weather_general(s, r):
        return [(f"What's the weather usually like in {s['month']}?",
                 f"{s['weather_general']} Forecasts change, so check a few days before and again each morning of the trip.")]

    @fam("pre")
    def ok_thanks(s, r):
        return [("Thanks, that helps a lot.", "Glad it helps. Ask anytime as you plan."),
                ("Perfect, noted.", "Great, sounds like things are coming together."),
                ("Ok cool.", "Sounds good."), ("Makes sense.", "Great."), ("Thank you!", "You're welcome.")]

    @fam("trip")
    def breakfast(s, r):
        out = []
        for town in s["towns"]:
            out.append((f"Good breakfast in {town}?",
                        f"In {town}, look for a bakery or cafe near the main street that opens early; they fill up fast in high "
                        f"season, so arriving before 8:30 helps. If you're heading out early, grab pastries and coffee to go and eat "
                        f"at the first viewpoint. Your lodging may also have breakfast included; check before paying twice."))
        return out

    @fam("trip")
    def dinner(s, r):
        out = []
        for town in s["towns"][:1]:
            out.append((f"We're tired. Easy dinner in {town} tonight?",
                        f"For an easy night in {town}, pick something casual close to where you're staying: pizza, a pub or diner, "
                        f"or takeaway eaten back at the room. Popular places can have a wait after 7 PM, so going a bit earlier helps. "
                        f"A grocery stop for tomorrow's snacks on the way back saves time in the morning."))
        return out

    @fam("trip")
    def laundry(s, r):
        return [("Where can we do laundry?",
                 "Ask your lodging first; many have guest laundry or can recommend a laundromat nearby. A load usually takes "
                 "about 90 minutes including drying, so it fits well into an evening or a lunch break. Pack a few detergent "
                 "pods and a mesh bag for next time.")]

    @fam("trip")
    def gas(s, r):
        if s["transport"] != "car":
            return []
        return [("Should I fill up the tank tonight?",
                 "Yes, fill up tonight when it's quiet; morning queues at the only station in town can be slow, and it means "
                 "you can leave straight away. Check tyre pressure while you're there if the warning light has come on.")]

    @fam("trip")
    def souvenirs(s, r):
        return [("Where's good for souvenirs?",
                 "Visitor-centre shops and small local craft stores usually have better-quality souvenirs than the shops right "
                 "next to the busiest attractions. Postcards, locally made food items and small crafts travel well. Leave it to "
                 "the last full day so you don't carry things around.")]

    @fam("trip", ("kids",))
    def kids_tired(s, r):
        return [("The kids were cranky this afternoon. Any ideas?",
                 "That's normal a few days into a trip. Build in downtime: a pool hour, a playground, or an early dinner and "
                 "screen time back at the room. Keeping lunch on time and snacks handy helps a lot.")]

    @fam("trip", ("elder",))
    def elder_tired(s, r):
        return [(f"{s['elder_name']} is a bit tired today.",
                 "Then take it slower today: shorter walks, more sitting stops with a view, and a relaxed lunch. Drinking enough "
                 "water helps more than people expect.")]

    @fam("trip")
    def photo_spot(s, r):
        out = []
        for name, _ in s["minor_sights"][:4]:
            out.append((f"Best time of day for photos at {name}?",
                        f"For {name}, early morning or the last two hours before sunset give the softest light and fewer people. "
                        f"Midday light is harsh but fine for quick snapshots. If it's cloudy, focus on details and close-ups."))
        return out

    @fam("trip")
    def parking(s, r):
        if s["transport"] != "car":
            return []
        return [("Is parking hard at the busy spots?",
                 "At the most popular stops, lots fill by mid-morning in busy periods. Arriving before about 9 AM or after "
                 "about 4 PM makes it much easier. If a lot is full, don't circle for long; go to the next stop and come back later.")]

    # NOTE: no filler may endorse idle time, cut a plan short, or discuss lodging choices (would confound ISD/AoC/STR).

    @fam("pre")
    def legs(s, r):
        out = []
        for a, b, t in s["legs"]:
            out.append((f"How long is the drive from {a} to {b}?" if s["transport"] == "car" else f"How long does it take to get from {a} to {b}?",
                        f"Plan on about {t} from {a} to {b} without long stops. Add time for fuel, food and photo stops, and more "
                        f"in busy periods. It's worth checking the route the morning you travel."))
        return out

    @fam("pre")
    def groceries(s, r):
        out = []
        for town in s["towns"][:2]:
            out.append((f"Is there a grocery store in {town}?",
                        f"Yes, {town} has places to buy groceries and snacks; prices in small tourist towns are higher than at "
                        f"home, so stocking up on basics in a bigger town on the way in can save money. Opening hours can be "
                        f"shorter on Sundays and holidays."))
        return out

    @fam("pre")
    def wildlife_safety(s, r):
        if not s.get("wildlife"):
            return []
        return [("Any wildlife safety rules we should know?",
                 f"{s['wildlife']} Never feed animals, keep food sealed in the car or room, and use pullouts rather than stopping "
                 f"in the road to watch wildlife.")]

    @fam("pre")
    def plugs_language(s, r):
        if not s.get("international"):
            return []
        return [("Do we need plug adapters?",
                 f"Check the plug type for {s['country']} and bring one adapter per person plus a small multi-socket USB charger; "
                 f"most phone and laptop chargers handle the voltage, but hair dryers often don't."),
                ("Should we learn any phrases?",
                 f"A few basics go a long way in {s['country']}: hello, please, thank you, excuse me and 'do you speak English?'. "
                 f"A translation app with the offline language pack downloaded covers menus and signs.")]

    @fam("pre")
    def checkin_times(s, r):
        return [("What are typical check-in and check-out times?",
                 "Typical check-in is mid-afternoon and check-out mid-morning, but it varies, so check each confirmation. Most "
                 "places will hold bags before check-in or after check-out if you ask.")]

    @fam("pre")
    def binoculars(s, r):
        return [("Worth bringing binoculars?",
                 "If you have a pair, yes: they're light and great for wildlife, birds and distant scenery. Not worth buying "
                 "expensive ones just for this trip.")]

    @fam("pre", ("kids",))
    def kid_gear(s, r):
        return [("Do we need anything special for the kids?",
                 "Comfortable shoes they've already worn in, a warm layer, a rain jacket, a small backpack each with their own "
                 "water bottle and snack, and something familiar for bedtime. A junior-ranger or activity booklet helps on longer stops.")]

    @fam("pre", ("teens", "adults", "couple", "elder"))
    def evening_ideas(s, r):
        out = []
        for town in s["towns"][:2]:
            out.append((f"Is there much to do in {town} in the evening?",
                        f"{town} is quiet in the evening compared with a city: dinner, a walk, maybe a pub or ice cream."))
        return out

    # ---- long planning exchanges (realistic volume: detailed day plans for the NON-★ days and revisions)
    VARIANTS = [
        ("Can you give me a detailed plan for {day}?", "base", "9:00"),
        ("What if it rains on {day}?", "rain", "9:30"),
        ("For {day}, we probably can't leave before 10. Can you redo it?", "late", "10:00"),
        ("Can you make {day} a bit more relaxed?", "relaxed", "9:30"),
        ("For {day}, where should we eat along the way?", "food", "9:00"),
        ("For {day}, what are the best photo moments?", "photo", "8:30"),
        ("Can you put {day} in a simple timeline I can screenshot?", "timeline", "9:00"),
        ("Any money-saving tips for {day}?", "budget", "9:00"),
    ]

    def _plan_text(s, day, sights, variant, start):
        h, m = map(int, start.split(":"))
        t = h * 60 + m
        lines = []
        for name, blurb in sights:
            dur = 50 if variant != "relaxed" else 70
            lines.append(f"**{t // 60}:{t % 60:02d}** {name}: {blurb} Allow about {dur} minutes.")
            t += dur + 25
            if len(lines) == 2:
                food = s["foods"][len(day) % len(s["foods"])]
                lines.append(f"**{t // 60}:{t % 60:02d}** Lunch break; a good chance to try {food}.")
                t += 60
        used = {n for n, _ in sights}
        spare = [x for x in s["minor_sights"] if x[0] not in used]
        k0 = len(day) % max(1, len(spare))
        spare = spare[k0:] + spare[:k0]
        while t < 16 * 60 + 30 and spare:
            extra = spare.pop(0)
            lines.append(f"**{t // 60}:{t % 60:02d}** {extra[0]}: {extra[1]} Allow about an hour.")
            t += 85
        if t < 16 * 60 + 30:
            lines.append(f"**{t // 60}:{t % 60:02d}** Free time in {s['towns'][0]} for a walk, shops or a café.")
            t = 16 * 60 + 45
        lines.append(f"**{t // 60}:{t % 60:02d}** Drive back to {s['towns'][0]} for dinner.")
        intro = {"base": f"Here's a comfortable plan for {day}:",
                 "rain": f"If it rains on {day}, keep the same order and lean on covered or drive-up viewpoints for the outdoor stops:",
                 "late": f"With a 10:00 start, here is {day}:",
                 "relaxed": f"A gentler version of {day}, with longer breaks:",
                 "food": f"For {day}, here's the plan with food stops built in:",
                 "photo": f"For photos on {day}, go early for soft light and save the busiest spot for later in the afternoon:",
                 "timeline": f"Simple timeline for {day}:",
                 "budget": f"Budget-friendly {day}: pack a picnic, bring refillable bottles, and use free viewpoints:"}[variant]
        tail = {"rain": " Bring rain layers and a dry change of socks; viewpoints can clear quickly after showers.",
                "budget": " Buying lunch supplies the evening before saves both money and time.",
                "photo": " A wide angle for scenery and a quick burst for wildlife work best on phones."}.get(variant, "")
        return intro + "\n\n" + "\n".join(lines) + ("\n\n" + tail.strip() if tail else "")

    @fam("pre")
    def day_plans(s, r):
        out = []
        days = s.get("plan_days", [])
        ms = s["minor_sights"]
        for di, day in enumerate(days):
            sights = [ms[(di * 3 + k) % len(ms)] for k in range(3)]
            for q, variant, start in VARIANTS:
                out.append((q.format(day=day), _plan_text(s, day, sights, variant, start)))
        return out

    @fam("trip")
    def compare_minor(s, r):
        out = []
        ms = s["minor_sights"]
        for i in range(len(ms)):
            for j in range(i + 1, len(ms)):
                if (i + j) % 2:
                    continue
                (a, ba), (b, bb) = ms[i], ms[j]
                out.append((f"If we only have time for one, {a} or {b}?",
                            f"Both are good, short stops. {a}: {ba} {b}: {bb} If you're tired or short on time, pick whichever "
                            f"is closer to your route that day; if you want the more memorable photo, go for the one with the "
                            f"better light at the time you'll be there (early morning or late afternoon)."))
        return out

    @fam("pre")
    def compare_minor_pre(s, r):
        out = []
        ms = s["minor_sights"]
        for i in range(len(ms)):
            for j in range(i + 1, len(ms)):
                if (i + j) % 2 == 0:
                    continue
                (a, ba), (b, bb) = ms[i], ms[j]
                out.append((f"Should we plan {a} and {b} on the same day?",
                            f"You can, if they're on the same side of your route. {a}: {ba} {b}: {bb} Together they make a "
                            f"pleasant half day with a lunch break between them."))
        return out

    @fam("trip")
    def minor_sight_trip(s, r):
        out = []
        for name, _ in s["minor_sights"][4:]:
            out.append((f"We're near {name}. Do we have time for a quick look?",
                        f"If you have 20–30 minutes, yes: {name} is a quick, easy stop. Park, take a short walk to the main view, "
                        f"and continue with your day."))
        return out

    @fam("trip")
    def lunch(s, r):
        out = []
        for town in s["towns"]:
            out.append((f"Quick lunch near {town}?",
                        f"Around {town}, a deli, cafe or bakery is quickest; picking up sandwiches to eat at a viewpoint saves "
                        f"time. If you'd rather sit down, go a little before noon to avoid the rush."))
        return out

    @fam("trip")
    def morning_start(s, r):
        return [("What time should we leave in the morning, generally?",
                 "In busy places, starting between 8 and 9 AM makes parking and crowds much easier. Pack the car the night before so the morning is quick.")]

    @fam("trip")
    def weather_today(s, r):
        return [("It's colder than expected this morning.",
                 "Mornings can be much colder than afternoons. Wear the warm layer now and keep it in the car; by midday you'll "
                 "probably shed it. Hot drinks at the first stop help.")]

    @fam("trip")
    def ok_thanks_trip(s, r):
        return [("Great, thanks!", "Enjoy it!"), ("Got it.", "Have a good one."), ("Will do.", "Sounds good, have fun.")]

    return F


FAMILIES = _fams()


def generate(slots, phase, n_pairs, seed, forbidden=()):
    """Return n_pairs (user, assistant) filler pairs for the phase, no repeats, deterministic for a seed."""
    rng = random.Random(seed)
    party = slots["party_type"]
    pool = []
    for ph, parties, fn in FAMILIES:
        if ph != phase:
            continue
        if parties != ("any",) and party not in parties:
            continue
        for pair in fn(slots, rng):
            pool.append(pair)
    low = [f.lower() for f in forbidden]
    pool = [p for p in pool if not any(w in (p[0] + p[1]).lower() for w in low)]
    rng.shuffle(pool)
    if n_pairs > len(pool):
        # allow reuse of chatter-only acknowledgements, never of substantive pairs
        acks = [p for p in pool if len(p[1]) < 60]
        while len(pool) < n_pairs and acks:
            pool.append(acks[len(pool) % len(acks)])
    return pool[:n_pairs]
