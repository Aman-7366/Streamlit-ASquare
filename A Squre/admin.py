"""
A Square - PRIVATE admin dashboard (separate from the public store).

Run:  streamlit run admin.py --server.port 8502 --server.address localhost
Customers never see this app. It shares asquare.db and product_images/ with app.py.
"""
import streamlit as st
from common import *  # noqa: F401,F403
from common import (BRAND, CATEGORIES, SIZES, PALETTE, ADMIN_PASSWORD, money,
                    run, save_images, img_paths)

st.set_page_config(page_title=f"{BRAND} Admin", page_icon="🔒", layout="wide")
apply_style()

ss = st.session_state
ss.setdefault("admin", False)

st.markdown(
    f'<div class="topbar"><div><div class="logo">A<span>²</span> {BRAND} Admin</div>'
    f'<div class="tag">Manage products, offers and orders</div></div></div>',
    unsafe_allow_html=True)


def page_admin():
    st.markdown('<div class="sec">Admin panel</div>', unsafe_allow_html=True)
    if not ss.admin:
        with st.form("login"):
            pw = st.text_input("Admin password", type="password")
            if st.form_submit_button("Login", type="primary"):
                if pw == ADMIN_PASSWORD:
                    ss.admin = True
                    st.rerun()
                else:
                    st.error("Wrong password")
        return

    if st.button("Logout"):
        ss.admin = False
        st.rerun()

    prods = run("SELECT * FROM products ORDER BY id DESC", fetch=True)
    orders = run("SELECT * FROM orders ORDER BY id DESC", fetch=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Products", len(prods))
    m2.metric("Orders", len(orders))
    m3.metric("Revenue", money(sum(o["total"] for o in orders)))
    m4.metric("Low stock (≤5)", len([p for p in prods if p["stock"] <= 5]))

    t1, t2, t3, t4 = st.tabs(["➕ Add product", "📦 Manage products", "🏷️ Offers", "🧾 Orders"])

    with t1:
        with st.form("add_product", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Product name *")
            cat = c2.selectbox("Category", CATEGORIES)
            c3, c4, c5 = st.columns(3)
            mrp = c3.number_input("MRP (original price) *", min_value=0.0, step=50.0)
            price = c4.number_input("Selling price *", min_value=0.0, step=50.0)
            stock = c5.number_input("Stock quantity", min_value=0, step=1, value=10)
            sizes = st.multiselect("Available sizes", SIZES, default=["S", "M", "L", "XL"])
            colors = st.text_input("Colours (comma separated)", placeholder="Black, Navy, Maroon")
            desc = st.text_area("Description (fabric, fit, care…)")
            files = st.file_uploader("Product photos (first one is the cover)", type=["jpg", "jpeg", "png", "webp"],
                                     accept_multiple_files=True)
            featured = st.checkbox("Show in 'Trending' section")
            if st.form_submit_button("Save product", type="primary"):
                if not name or price <= 0:
                    st.error("Name and selling price are required.")
                else:
                    names = save_images(files)
                    run("""INSERT INTO products(name,category,price,mrp,sizes,colors,stock,description,
                           images,featured,created) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (name, cat, price, max(mrp, price), ",".join(sizes), colors, stock, desc,
                         ",".join(names), int(featured), datetime.now().isoformat()))
                    st.success(f"'{name}' added!")

    with t2:
        q = st.text_input("Search your products", key="admin_q")
        for p in prods:
            if q and q.lower() not in p["name"].lower():
                continue
            status = "" if p["active"] else " (hidden)"
            with st.expander(f"{p['name']}  |  {money(p['price'])}  |  stock {p['stock']}{status}"):
                c1, c2 = st.columns([1, 3])
                imgs = img_paths(p)
                if imgs:
                    c1.image(imgs[0])
                with c2.form(f"edit{p['id']}"):
                    n = st.text_input("Name", p["name"])
                    a, b, c = st.columns(3)
                    mrp = a.number_input("MRP", value=float(p["mrp"]), step=50.0)
                    pr = b.number_input("Price", value=float(p["price"]), step=50.0)
                    stk = c.number_input("Stock", value=int(p["stock"]), step=1, min_value=0)
                    ds = st.text_area("Description", p["description"] or "")
                    more = st.file_uploader("Add more photos", type=["jpg", "jpeg", "png", "webp"],
                                            accept_multiple_files=True, key=f"up{p['id']}")
                    f1, f2 = st.columns(2)
                    feat = f1.checkbox("Trending", bool(p["featured"]))
                    act = f2.checkbox("Visible in store", bool(p["active"]))
                    s1, s2 = st.columns(2)
                    save = s1.form_submit_button("Save changes", type="primary")
                    delete = s2.form_submit_button("Delete product")
                if save:
                    new_imgs = save_images(more)
                    allimgs = ",".join([x for x in [p["images"]] + new_imgs if x])
                    run("""UPDATE products SET name=?,mrp=?,price=?,stock=?,description=?,images=?,
                           featured=?,active=? WHERE id=?""",
                        (n, max(mrp, pr), pr, stk, ds, allimgs, int(feat), int(act), p["id"]))
                    st.success("Saved")
                    st.rerun()
                if delete:
                    run("DELETE FROM products WHERE id=?", (p["id"],))
                    st.rerun()

    with t3:
        st.markdown("**Create a new offer / coupon**")
        with st.form("add_offer", clear_on_submit=True):
            o1, o2 = st.columns(2)
            title = o1.text_input("Banner title *", placeholder="Festive Sale: Flat 25% off")
            sub = o2.text_input("Subtitle", placeholder="On all ethnic wear")
            o3, o4, o5, o6 = st.columns(4)
            code = o3.text_input("Coupon code (optional)").strip().upper()
            pct = o4.number_input("Discount %", 0, 90, 10)
            minord = o5.number_input("Min. order (₹)", 0, 100000, 0, step=100)
            till = o6.date_input("Valid till", value=None)
            colr = st.selectbox("Banner colour", list(PALETTE.keys()))
            if st.form_submit_button("Publish offer", type="primary"):
                if not title:
                    st.error("Title is required")
                else:
                    run("INSERT INTO offers(title,subtitle,code,discount_pct,min_order,valid_till,color) VALUES(?,?,?,?,?,?,?)",
                        (title, sub, code, pct, minord, till.isoformat() if till else "", colr))
                    st.success("Offer is live!")
                    st.rerun()
        st.markdown("**Existing offers**")
        for o in run("SELECT * FROM offers ORDER BY id DESC", fetch=True):
            c1, c2, c3 = st.columns([4, 1, 1])
            state = "🟢 live" if o["active"] else "⚪ paused"
            c1.write(f"**{o['title']}**  ({o['code'] or 'no code'}, {o['discount_pct']}% off) {state}")
            if c2.button("Pause/Resume", key=f"t{o['id']}"):
                run("UPDATE offers SET active=1-active WHERE id=?", (o["id"],))
                st.rerun()
            if c3.button("Delete", key=f"x{o['id']}"):
                run("DELETE FROM offers WHERE id=?", (o["id"],))
                st.rerun()

    with t4:
        if not orders:
            st.info("No orders yet.")
        for o in orders:
            with st.expander(f"#{o['id']}  {o['customer']}  |  {money(o['total'])}  |  {o['status']}  |  {o['created']}"):
                st.write(f"📞 {o['phone']}")
                st.write(f"📍 {o['address']}")
                for it in json.loads(o["items"]):
                    st.write(f"- {it['name']} ({it['size']}) × {it['qty']}")
                if o["coupon"]:
                    st.write(f"Coupon used: {o['coupon']}")
                new = st.selectbox("Status", ["New", "Packed", "Shipped", "Delivered", "Cancelled"],
                                   index=["New", "Packed", "Shipped", "Delivered", "Cancelled"].index(o["status"]),
                                   key=f"st{o['id']}")
                if new != o["status"]:
                    run("UPDATE orders SET status=? WHERE id=?", (new, o["id"]))
                    st.rerun()




page_admin()
