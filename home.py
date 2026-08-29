from database import log_activity_db
import streamlit as st


def show_home_interface():
  st.markdown(
      '<div class="apex-title">پڕۆژەی ئەپێکس - چاودێری ئەمنی</div>',
      unsafe_allow_html=True,
  )
  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    if not st.session_state["show_options"]:
      if st.button("دەست پێکردن", key="start_btn"):
        st.session_state["show_options"] = True
        st.rerun()
    else:
      if st.session_state["selected_sector"] is None:
        st.markdown(
            "<p style='text-align: center; color: white; font-weight:"
            " bold;'>تکایە جۆری بەکارهێنان هەڵبژێرە:</p>",
            unsafe_allow_html=True,
        )
        if st.button("بەکارهێنانی ئەپێکس بۆ ماڵەوە", key="sec_home"):
          st.session_state["selected_sector"] = "ماڵەوە"
          st.rerun()
        if st.button("بەکارهێنانی ئەپێکس بۆ شوێنی بازرگانی", key="sec_biz"):
          st.session_state["selected_sector"] = "بازرگانی"
          st.rerun()
        if st.button(
            "بەکارهێنانی ئەپێکس بۆ دەزگا حکومیەکان و ئەمنیەکان", key="sec_gov"
        ):
          st.session_state["selected_sector"] = "حکومی و ئەمنی"
          st.rerun()
        if st.button("گەڕانەوە", key="back_btn"):
          st.session_state["show_options"] = False
          st.rerun()
      else:
        sector_name = st.session_state["selected_sector"]
        st.markdown(
            f"<p style='text-align: center; color: #00ff66; font-weight:"
            f" bold;'>پاسوۆردی بەشی ({sector_name}) بنووسە:</p>",
            unsafe_allow_html=True,
        )

        sector_pass = st.text_input(
            "پاسوۆردی بەش",
            type="password",
            key="sector_pass_field",
            placeholder="پاسوۆرد بنووسە...",
        )

        if st.button("دڵنیاکردنەوەی پاسوۆرد", key="verify_sector_pass"):
          current_sector = st.session_state["selected_sector"]
          pass_dict = {"ماڵەوە": "1111", "بازرگانی": "2222", "حکومی و ئەمنی": "9999"}

          if (
              current_sector in pass_dict
              and sector_pass == pass_dict[current_sector]
          ):
            st.session_state["password_correct"] = True
            log_activity_db("SUCCESS", f"Logged into Sector: {current_sector}")
            st.rerun()
          else:
            log_activity_db(
                "WARNING", f"Failed sector login: {current_sector}"
            )
            st.error("⚠️ پاسوۆردی ئەم بەشە هەڵەیە!")

        if st.button("گەڕانەوە بۆ هەڵبژاردنی بەشەکان", key="back_to_sec"):
          st.session_state["selected_sector"] = None
          st.rerun()