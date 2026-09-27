import streamlit as st
import sqlite3
import bcrypt
import itertools

DB_NAME = "halisaha.db"

def get_db():
    return sqlite3.connect(DB_NAME)

def check_login(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, password_hash, is_admin FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row and bcrypt.checkpw(password.encode("utf-8"), row[1].encode("utf-8")):
        return row[0], bool(row[2])
    return None, False

def register_user(username, password):
    conn = get_db()
    c = conn.cursor()
    salt = bcrypt.gensalt()
    pw_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    try:
        c.execute("INSERT INTO users (username, password_hash, is_gk, is_admin) VALUES (?, ?, 0, 0)",
                  (username.strip(), pw_hash))
        conn.commit()
        success = True
        msg = "Kayıt başarılı! Şimdi bu bilgilerle giriş yapabilirsiniz."
    except sqlite3.IntegrityError:
        success = False
        msg = f"'{username}' kullanıcı adı zaten alınmış! Lütfen başka bir ad deneyin."
    conn.close()
    return success, msg

def get_all_players():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, is_gk FROM users WHERE username != 'admin' ORDER BY is_gk DESC, username ASC")
    players = c.fetchall()
    conn.close()
    return players

def add_player(username, password, is_gk):
    conn = get_db()
    c = conn.cursor()
    salt = bcrypt.gensalt()
    pw_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    try:
        c.execute("INSERT INTO users (username, password_hash, is_gk, is_admin) VALUES (?, ?, ?, 0)",
                  (username.strip(), pw_hash, 1 if is_gk else 0))
        conn.commit()
        success = True
        msg = f"'{username}' başarıyla sisteme eklendi."
    except sqlite3.IntegrityError:
        success = False
        msg = f"'{username}' adında bir kullanıcı zaten mevcut!"
    conn.close()
    return success, msg

def update_player(user_id, new_username, is_gk):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET username = ?, is_gk = ? WHERE id = ?",
                  (new_username.strip(), 1 if is_gk else 0, user_id))
        conn.commit()
        success = True
        msg = "Oyuncu bilgileri güncellendi."
    except sqlite3.IntegrityError:
        success = False
        msg = f"'{new_username}' kullanıcı adı başka bir oyuncu tarafından kullanılıyor!"
    conn.close()
    return success, msg

def delete_player(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM ratings WHERE rater_id = ? OR target_id = ?", (user_id, user_id))
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def save_ratings_batch(rater_id, ratings_dict):
    conn = get_db()
    c = conn.cursor()
    for target_id, score in ratings_dict.items():
        c.execute("""
        INSERT INTO ratings (rater_id, target_id, score)
        VALUES (?, ?, ?)
        ON CONFLICT(rater_id, target_id) DO UPDATE SET score=excluded.score
        """, (rater_id, target_id, score))
    conn.commit()
    conn.close()

def get_player_averages():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    SELECT u.id, u.username, u.is_gk, 
           ROUND(COALESCE(AVG(r.score), 5.0), 2) as avg_score,
           COUNT(r.score) as vote_count
    FROM users u
    LEFT JOIN ratings r ON u.id = r.target_id
    WHERE u.username != 'admin'
    GROUP BY u.id
    ORDER BY avg_score DESC
    """)
    stats = c.fetchall()
    conn.close()
    return stats

def balance_teams(players_stats):
    gks = [p for p in players_stats if p[2] == 1]
    field = [p for p in players_stats if p[2] == 0]
    
    if len(gks) < 2 or len(field) < 12:
        return None, None, f"Dengeleme için 2 kaleci ve 12 saha oyuncusu gerekir. Mevcut: {len(gks)} kaleci, {len(field)} saha oyuncusu."
    
    gk_a, gk_b = gks[0], gks[1]
    best_diff = float("inf")
    best_team_a = []
    best_team_b = []
    
    for team_a_field in itertools.combinations(field, 6):
        team_a_set = set(team_a_field)
        team_b_field = [p for p in field if p not in team_a_set]
        
        score_a = gk_a[3] + sum(p[3] for p in team_a_field)
        score_b = gk_b[3] + sum(p[3] for p in team_b_field)
        
        diff = abs(score_a - score_b)
        if diff < best_diff:
            best_diff = diff
            best_team_a = [gk_a] + list(team_a_field)
            best_team_b = [gk_b] + team_b_field

    return best_team_a, best_team_b, best_diff

st.set_page_config(page_title="7v7 Halı Saha Portalı", layout="wide")
st.title("⚽ 7v7 Halı Saha Portalı")

if "user_id" not in st.session_state:
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False

# GİRİŞ VEYA KAYIT EKRANI
if not st.session_state.user_id:
    tab_login, tab_reg = st.tabs(["🔑 Giriş Yap", "📝 Yeni Hesap Oluştur (Kayıt Ol)"])

    with tab_login:
        st.subheader("Giriş Yap")
        col1, _ = st.columns([1, 1])
        with col1:
            u_name = st.text_input("Kullanıcı Adı", key="login_u")
            u_pass = st.text_input("Şifre", type="password", key="login_p")
            if st.button("Giriş Yap", key="btn_login"):
                uid, is_admin = check_login(u_name.strip(), u_pass)
                if uid:
                    st.session_state.user_id = uid
                    st.session_state.username = u_name.strip()
                    st.session_state.is_admin = is_admin
                    st.success("Giriş başarılı!")
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı!")

    with tab_reg:
        st.subheader("Kayıt Ol")
        st.caption("Kendi kullanıcı adınızı ve şifrenizi belirleyerek sisteme katılın ve oy kullanın.")
        col1, _ = st.columns([1, 1])
        with col1:
            reg_u = st.text_input("Kullanıcı Adı Belirleyin", key="reg_u")
            reg_p = st.text_input("Şifre Belirleyin", type="password", key="reg_p")
            reg_p_confirm = st.text_input("Şifreyi Tekrar Girin", type="password", key="reg_pc")
            
            if st.button("Hesap Oluştur", key="btn_register"):
                if not reg_u.strip() or not reg_p:
                    st.warning("Lütfen kullanıcı adı ve şifre alanlarını boş bırakmayın.")
                elif reg_p != reg_p_confirm:
                    st.error("Girdiğiniz şifreler birbiriyle uyuşmuyor!")
                elif reg_u.strip().lower() == "admin":
                    st.error("'admin' adıyla kayıt olunamaz!")
                else:
                    ok, msg = register_user(reg_u, reg_p)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
else:
    st.sidebar.markdown(f"👤 Aktif Kullanıcı: **{st.session_state.username}**")
    if st.session_state.is_admin:
        st.sidebar.success("🛡️ Yetki: **Yönetici (Admin)**")
    else:
        st.sidebar.info("🏃 Yetki: **Oyuncu / Seçmen**")

    if st.sidebar.button("Oturumu Kapat"):
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.is_admin = False
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Güncel Puan Durumu")
    st.sidebar.caption("Tüm kullanıcıların verdiği oyların canlı ortalaması:")
    
    current_stats = get_player_averages()
    for _, pname, is_gk, avg_score, vote_count in current_stats:
        tag = "🧤 [K]" if is_gk else "🏃"
        st.sidebar.write(f"{tag} **{pname}**: `{avg_score:.2f}` ⭐ _({vote_count} oy)_")

    if st.session_state.is_admin:
        tab_rate, tab_match, tab_manage = st.tabs(["⭐ Oyuncuları Puanla", "⚖️ Takımları Eşleştir (Admin)", "⚙️ Oyuncu Yönetimi (Admin)"])
    else:
        tab_rate = st.container()
        tab_match = None
        tab_manage = None

    with tab_rate:
        st.subheader("Oyuncuları Puanla")
        st.caption("1 (En Zayıf) - 10 (En İyi) arasında puanlayın ve alttaki butona basarak kaydedin.")

        players = get_all_players()
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT target_id, score FROM ratings WHERE rater_id = ?", (st.session_state.user_id,))
        existing_scores = dict(c.fetchall())
        conn.close()

        with st.form("rating_form"):
            temp_scores = {}
            for pid, pname, is_gk in players:
                role = " 🧤 (Kaleci)" if is_gk else ""
                current_val = existing_scores.get(pid, 5)
                temp_scores[pid] = st.slider(f"{pname}{role}", 1, 10, current_val, key=f"p_{pid}")

            if st.form_submit_button("Puanları Kaydet ve Güncelle"):
                save_ratings_batch(st.session_state.user_id, temp_scores)
                st.success("Puanlar başarıyla kaydedildi! Yan paneldeki ortalamalar güncellendi.")
                st.rerun()

    if tab_match is not None:
        with tab_match:
            st.subheader("⚖️ Otomatik 7v7 Kadro Dengeleyici")
            st.write("Sistemdeki güncel oy ortalamalarını kullanarak en dengeli iki takımı oluşturur.")

            if st.button("Dengeli Takımları Hesapla"):
                stats = get_player_averages()
                team_a, team_b, diff = balance_teams(stats)

                if team_a and team_b:
                    score_a = sum(p[3] for p in team_a)
                    score_b = sum(p[3] for p in team_b)

                    c1, c2 = st.columns(2)
                    with c1:
                        st.success(f"### Takım A (Toplam Güç: {score_a:.2f})")
                        for p in team_a:
                            role = "🧤 Kaleci" if p[2] == 1 else "🏃 Saha"
                            st.write(f"- **{p[1]}** ({role}) - Ort: `{p[3]:.2f}`")

                    with c2:
                        st.info(f"### Takım B (Toplam Güç: {score_b:.2f})")
                        for p in team_b:
                            role = "🧤 Kaleci" if p[2] == 1 else "🏃 Saha"
                            st.write(f"- **{p[1]}** ({role}) - Ort: `{p[3]:.2f}`")

                    st.markdown("---")
                    st.metric(label="Takımlar Arası Güç Farkı", value=f"{diff:.2f}", delta="0'a ne kadar yakınsa o kadar dengeli", delta_color="inverse")
                else:
                    st.error(diff)

    if tab_manage is not None:
        with tab_manage:
            st.subheader("⚙️ Oyuncu Ekle, Düzenle veya Sil")
            
            with st.expander("➕ Yeni Oyuncu Ekle", expanded=False):
                with st.form("add_player_form"):
                    col_u, col_p, col_r = st.columns([2, 2, 1])
                    with col_u:
                        new_name = st.text_input("Kullanıcı Adı")
                    with col_p:
                        new_pass = st.text_input("Şifre", value="1234")
                    with col_r:
                        new_role = st.selectbox("Mevki", ["Saha Oyuncusu", "Kaleci"])
                    
                    if st.form_submit_button("Oyuncuyu Kaydet"):
                        if new_name.strip():
                            is_gk = (new_role == "Kaleci")
                            ok, msg = add_player(new_name, new_pass, is_gk)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                        else:
                            st.warning("Lütfen bir kullanıcı adı girin.")

            st.markdown("---")
            st.write("### Mevcut Oyuncu Listesi")

            all_players = get_all_players()
            gks = [p for p in all_players if p[2] == 1]
            fields = [p for p in all_players if p[2] == 0]
            st.caption(f"Toplam Oyuncu: **{len(all_players)}** | Kaleci: **{len(gks)}** | Saha: **{len(fields)}** (7v7 maç için 2 kaleci + 12 saha oyuncusu gerekir)")

            for pid, pname, is_gk in all_players:
                with st.container():
                    c_name, c_role, c_save, c_del = st.columns([3, 2, 1.5, 1])
                    with c_name:
                        edited_name = st.text_input(f"İsim_{pid}", value=pname, label_visibility="collapsed")
                    with c_role:
                        role_idx = 1 if is_gk else 0
                        edited_role = st.selectbox(f"Mevki_{pid}", ["Saha Oyuncusu", "Kaleci"], index=role_idx, label_visibility="collapsed")
                    with c_save:
                        if st.button("💾 Güncelle", key=f"btn_up_{pid}"):
                            ok, msg = update_player(pid, edited_name, edited_role == "Kaleci")
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    with c_del:
                        if st.button("🗑️ Sil", key=f"btn_del_{pid}"):
                            delete_player(pid)
                            st.warning(f"{pname} silindi.")
                            st.rerun()
