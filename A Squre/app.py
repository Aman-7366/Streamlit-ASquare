"""
A Square  -  Wear Your Own Fashion
Customer-facing online store (Flipkart / Myntra style).

Run:  streamlit run app.py
The admin dashboard is a SEPARATE app: see admin.py
"""
import streamlit as st
from common import *  # noqa: F401,F403
from common import BRAND, TAGLINE, WHATSAPP_NUMBER, CURRENCY, CATEGORIES

st.set_page_config(page_title=f"{BRAND} | {TAGLINE}", page_icon="🛍️", layout="wide")
apply_style()

# ----------------------------------------------------------------------------
# STATE
# ----------------------------------------------------------------------------
ss = st.session_state
ss.setdefault("page", "home")
ss.setdefault("pid", None)
ss.setdefault("cart", {})  # key "pid|size" -> qty
ss.setdefault("coupon", None)


def go(page, pid=None):
    ss.page, ss.pid = page, pid


def cart_count():
    return sum(ss.cart.values())


def get_product(pid):
    r = run("SELECT * FROM products WHERE id=?", (pid,), fetch=True)
    return r[0] if r else None


# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------
def header():
    st.markdown(
        f'<div class="topbar"><div><div class="logo">A<span>²</span> {BRAND}</div>'
        f'<div class="tag">{TAGLINE}</div></div></div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns([1, 4, 1, 1])
    with c1:
        st.write("")
        if st.button("🏠 Home", use_container_width=True):
            go("home")
            st.rerun()
    with c2:
        ss.search = st.text_input("Search", value=ss.get("search", ""),
                                  placeholder="Search for shirts, kurtas, dresses, brands…",
                                  label_visibility="collapsed")
    with c3:
        if st.button("🔥 Offers", use_container_width=True):
            go("offers")
            st.rerun()
    with c4:
        if st.button(f"🛒 Cart ({cart_count()})", use_container_width=True):
            go("cart")
            st.rerun()
    ss.setdefault("cat", "All")
    cats = ["All"] + CATEGORIES
    st.markdown('<div class="strip"></div>', unsafe_allow_html=True)
    ss.cat = st.radio("Category", cats, horizontal=True, index=cats.index(ss.cat),
                      label_visibility="collapsed")


# ----------------------------------------------------------------------------
# COMPONENTS
# ----------------------------------------------------------------------------
def offer_banner(o):
    bg = PALETTE.get(o["color"], PALETTE["plum"])
    code = f'<div class="code">USE CODE: {o["code"]}</div>' if o["code"] else ""
    till = f' &nbsp;•&nbsp; valid till {o["valid_till"]}' if o["valid_till"] else ""
    st.markdown(
        f'<div class="hero" style="background:{bg}"><h2>{o["title"]}</h2>'
        f'<p>{o["subtitle"] or ""}{till}</p>{code}</div>', unsafe_allow_html=True)


def product_card(p, key):
    with st.container(border=True):
        imgs = img_paths(p)
        if imgs:
            st.image(imgs[0], use_container_width=True)
        else:
            st.markdown('<div class="noimg">No photo yet</div>', unsafe_allow_html=True)
        d = discount_pct(p)
        st.markdown(f'<div class="pname">{p["name"]}</div><div class="pcat">{p["category"]}</div>',
                    unsafe_allow_html=True)
        extra = f'<span class="mrp">{money(p["mrp"])}</span><span class="off">{d}% off</span>' if d else ""
        st.markdown(f'<span class="price">{money(p["price"])}</span>{extra}', unsafe_allow_html=True)
        if p["stock"] <= 0:
            st.markdown('<span class="low">Out of stock</span>', unsafe_allow_html=True)
        elif p["stock"] <= 5:
            st.markdown(f'<span class="low">Only {p["stock"]} left</span>', unsafe_allow_html=True)
        if st.button("View", key=f"v{key}{p['id']}", use_container_width=True):
            go("product", p["id"])
            st.rerun()


def grid(products, cols=4, prefix="g"):
    if not products:
        st.info("No products found. Try another search or category.")
        return
    for i in range(0, len(products), cols):
        row = st.columns(cols)
        for col, p in zip(row, products[i:i + cols]):
            with col:
                product_card(p, prefix)


# ----------------------------------------------------------------------------
# PAGES - STOREFRONT
# ----------------------------------------------------------------------------
def page_home():
    offers = active_offers()
    if offers:
        idx = st.session_state.get("banner", 0) % len(offers)
        offer_banner(offers[idx])
        if len(offers) > 1:
            b1, b2, _ = st.columns([1, 1, 8])
            if b1.button("◀"):
                ss.banner = idx - 1
                st.rerun()
            if b2.button("▶"):
                ss.banner = idx + 1
                st.rerun()
    else:
        st.markdown(f'<div class="hero" style="background:{PALETTE["plum"]}"><h2>{TAGLINE}</h2>'
                    f'<p>New styles, made to be yours.</p></div>', unsafe_allow_html=True)

    # Filters
    f1, f2, f3 = st.columns([2, 2, 2])
    sort = f1.selectbox("Sort by", ["Newest", "Price: Low to High", "Price: High to Low", "Biggest Discount"])
    maxp = int((run("SELECT MAX(price) m FROM products", fetch=True)[0]["m"] or 5000))
    price_rng = f2.slider("Price range", 0, max(maxp, 1000), (0, max(maxp, 1000)))
    in_stock = f3.checkbox("In stock only", value=False)

    sql, params = "SELECT * FROM products WHERE active=1", []
    if ss.cat != "All":
        sql += " AND category=?"
        params.append(ss.cat)
    if ss.get("search"):
        sql += " AND (name LIKE ? OR description LIKE ? OR category LIKE ?)"
        s = f"%{ss.search}%"
        params += [s, s, s]
    sql += " AND price BETWEEN ? AND ?"
    params += list(price_rng)
    if in_stock:
        sql += " AND stock>0"
    products = run(sql, tuple(params), fetch=True)
    if sort == "Newest":
        products.sort(key=lambda p: p["id"], reverse=True)
    elif sort == "Price: Low to High":
        products.sort(key=lambda p: p["price"])
    elif sort == "Price: High to Low":
        products.sort(key=lambda p: -p["price"])
    else:
        products.sort(key=discount_pct, reverse=True)

    featured = [p for p in products if p["featured"]]
    if featured and ss.cat == "All" and not ss.get("search"):
        st.markdown('<div class="sec">Trending at A Square</div>', unsafe_allow_html=True)
        grid(featured[:4], 4, "f")
    deals = [p for p in products if discount_pct(p) >= 30]
    if deals and ss.cat == "All" and not ss.get("search"):
        st.markdown('<div class="sec">Deals of the day: 30% off or more</div>', unsafe_allow_html=True)
        grid(sorted(deals, key=discount_pct, reverse=True)[:4], 4, "d")

    title = "All products" if ss.cat == "All" else ss.cat
    st.markdown(f'<div class="sec">{title} ({len(products)})</div>', unsafe_allow_html=True)
    grid(products, 4, "a")


def page_offers():
    st.markdown('<div class="sec">Offers and coupons</div>', unsafe_allow_html=True)
    offers = active_offers()
    if not offers:
        st.info("No live offers right now. Check back soon!")
    for o in offers:
        offer_banner(o)


def page_product():
    p = get_product(ss.pid)
    if not p:
        st.warning("Product not found.")
        return
    if st.button("← Back to shopping"):
        go("home")
        st.rerun()
    left, right = st.columns([1, 1.1])
    imgs = img_paths(p)
    with left:
        if imgs:
            st.image(imgs[0], use_container_width=True)
            if len(imgs) > 1:
                tcols = st.columns(min(len(imgs) - 1, 4))
                for c, im in zip(tcols, imgs[1:5]):
                    c.image(im, use_container_width=True)
        else:
            st.markdown('<div class="noimg" style="height:420px">No photo yet</div>', unsafe_allow_html=True)
    with right:
        st.markdown(f'<div class="pcat">{p["category"]}</div>', unsafe_allow_html=True)
        st.markdown(f"## {p['name']}")
        d = discount_pct(p)
        extra = f'<span class="mrp">{money(p["mrp"])}</span><span class="off">{d}% off</span>' if d else ""
        st.markdown(f'<span class="price" style="font-size:30px">{money(p["price"])}</span>{extra}',
                    unsafe_allow_html=True)
        st.caption("Inclusive of all taxes")
        sizes = [s for s in (p["sizes"] or "").split(",") if s]
        size = st.radio("Select size", sizes, horizontal=True) if sizes else "Free Size"
        if p["colors"]:
            st.write(f"**Colours:** {p['colors']}")
        if p["stock"] <= 0:
            st.error("Out of stock")
        else:
            if p["stock"] <= 5:
                st.markdown(f'<span class="low">Hurry! Only {p["stock"]} left</span>', unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            if b1.button("🛒 Add to cart", type="primary", use_container_width=True):
                k = f"{p['id']}|{size}"
                ss.cart[k] = ss.cart.get(k, 0) + 1
                st.toast("Added to cart")
                st.rerun()
            if b2.button("⚡ Buy now", use_container_width=True):
                k = f"{p['id']}|{size}"
                ss.cart[k] = ss.cart.get(k, 0) + 1
                go("cart")
                st.rerun()
        st.markdown("#### Product details")
        st.write(p["description"] or "—")

    related = run("SELECT * FROM products WHERE active=1 AND category=? AND id!=? LIMIT 4",
                  (p["category"], p["id"]), fetch=True)
    if related:
        st.markdown('<div class="sec">You may also like</div>', unsafe_allow_html=True)
        grid(related, 4, "r")


def cart_totals():
    lines, subtotal = [], 0
    for k, qty in list(ss.cart.items()):
        pid, size = k.split("|")
        p = get_product(int(pid))
        if not p:
            del ss.cart[k]
            continue
        lines.append((k, p, size, qty))
        subtotal += p["price"] * qty
    discount = 0
    if ss.coupon:
        o = ss.coupon
        if subtotal >= (o["min_order"] or 0):
            discount = subtotal * o["discount_pct"] / 100
    return lines, subtotal, discount


def page_cart():
    st.markdown('<div class="sec">Your cart</div>', unsafe_allow_html=True)
    lines, subtotal, discount = cart_totals()
    if not lines:
        st.info("Your cart is empty. Find something you love!")
        if st.button("Start shopping", type="primary"):
            go("home")
            st.rerun()
        return
    left, right = st.columns([2, 1])
    with left:
        for k, p, size, qty in lines:
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 3, 1.4])
                imgs = img_paths(p)
                if imgs:
                    c1.image(imgs[0], use_container_width=True)
                c2.markdown(f"**{p['name']}**  \nSize: {size}  \n{money(p['price'])} × {qty}")
                a, b, c = c3.columns(3)
                if a.button("➖", key=f"m{k}"):
                    ss.cart[k] -= 1
                    if ss.cart[k] <= 0:
                        del ss.cart[k]
                    st.rerun()
                if b.button("➕", key=f"p{k}"):
                    ss.cart[k] += 1
                    st.rerun()
                if c.button("🗑", key=f"d{k}"):
                    del ss.cart[k]
                    st.rerun()
    with right:
        with st.container(border=True):
            st.markdown("**Price details**")
            code = st.text_input("Coupon code", placeholder="e.g. WELCOME10").strip().upper()
            if st.button("Apply coupon"):
                match = [o for o in active_offers() if o["code"] and o["code"].upper() == code]
                if match:
                    ss.coupon = match[0]
                    st.rerun()
                else:
                    st.error("Invalid or expired coupon")
            if ss.coupon:
                st.success(f"{ss.coupon['code']} applied ({ss.coupon['discount_pct']}% off)")
                if subtotal < (ss.coupon["min_order"] or 0):
                    st.warning(f"Add items worth {money(ss.coupon['min_order'] - subtotal)} more to use this coupon.")
            st.write(f"Subtotal: {money(subtotal)}")
            st.write(f"Coupon discount: -{money(discount)}")
            total = subtotal - discount
            st.markdown(f"### Total: {money(total)}")

        with st.form("checkout"):
            st.markdown("**Delivery details**")
            name = st.text_input("Full name")
            phone = st.text_input("Phone number")
            addr = st.text_area("Address")
            ok = st.form_submit_button("Place order", type="primary", use_container_width=True)
        if ok:
            if not (name and phone and addr):
                st.error("Please fill in name, phone and address.")
            else:
                items = [{"id": p["id"], "name": p["name"], "size": s, "qty": q, "price": p["price"]}
                         for _, p, s, q in lines]
                run("INSERT INTO orders(customer,phone,address,items,total,coupon,created) VALUES(?,?,?,?,?,?,?)",
                    (name, phone, addr, json.dumps(items), total,
                     ss.coupon["code"] if ss.coupon else "", datetime.now().strftime("%Y-%m-%d %H:%M")))
                for it in items:
                    run("UPDATE products SET stock=MAX(stock-?,0) WHERE id=?", (it["qty"], it["id"]))
                msg = f"New order for {BRAND}\nName: {name}\nPhone: {phone}\nAddress: {addr}\n"
                msg += "\n".join(f"- {i['name']} ({i['size']}) x{i['qty']}" for i in items)
                msg += f"\nTotal: {money(total)}"
                ss.cart, ss.coupon = {}, None
                st.success("Order placed! We will contact you shortly.")
                st.link_button("Confirm on WhatsApp",
                               f"https://wa.me/{WHATSAPP_NUMBER}?text={urllib.parse.quote(msg)}")




# ----------------------------------------------------------------------------
# ROUTER
# ----------------------------------------------------------------------------
header()
{"home": page_home, "offers": page_offers, "product": page_product, "cart": page_cart}[ss.page]()

st.markdown(
    f'<div class="footer"><b style="color:#fff;font-size:20px">A² {BRAND}</b><br>'
    f'<i>{TAGLINE}</i><br><span style="font-size:13px">© {date.today().year} {BRAND}. All rights reserved.</span></div>',
    unsafe_allow_html=True)
