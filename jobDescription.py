import streamlit as st

class JobDescriptionManager:
    def __init__(self, job_descriptions):
        st.subheader("Select Job Title")
        self.job_title = st.selectbox("Choose a job title", options=list(job_descriptions.keys()))
        # Store job descriptions in session state
        if "job_descriptions" not in st.session_state:
            st.session_state["job_descriptions"] = job_descriptions

    def get_job_details(self):
        return st.session_state["job_descriptions"].get(self.job_title, {})

    def get_city_from_pincode(self, pincode):
        # Example mapping; in real-world scenarios, use an API or a full database.
        pincode_city_mapping = {
            "110001": "New Delhi",
            "400001": "Mumbai",
            "560001": "Bangalore",
            "440001": "Nagpur",
            "411014": "Pune",
        }

        return pincode_city_mapping.get(pincode, pincode)


    def update_job_description(self, skills, project_domains, experience, locations, must_to_have, good_to_have):
        updated_locations = list(set([
            self.get_city_from_pincode(loc) if loc.isdigit() else loc for loc in locations
        ]))
        print("Updated Locations:", updated_locations)
        st.session_state["job_descriptions"][self.job_title] = {
            "skills": skills,
            "ProjectDomain": project_domains,
            "Experience": experience,
            "Location": updated_locations,
            "Must to have": must_to_have,
            "Good to have": good_to_have,
        }
        st.session_state["editing"] = None

    def JDEditor(self):
        job_info = self.get_job_details()

        if st.button("✏️ Edit Job Description"):
            st.session_state["editing"] = self.job_title

        if "editing" in st.session_state and st.session_state["editing"] == self.job_title:
            st.subheader(f"🔹 Editing: {self.job_title}")

            with st.expander("💡 Required Skills"):
                skills = st.text_area("Skills (comma-separated)", ", ".join(job_info.get("skills", []))).split(", ")

            with st.expander("🌍 Project Domains"):
                project_domains = st.text_area("Project Domains (comma-separated)", ", ".join(job_info.get("ProjectDomain", []))).split(", ")

            with st.expander("⌛ Experience Required"):
                experience = st.text_area("Experience (comma-separated)", ", ".join(job_info.get("Experience", []))).split(", ")

            with st.expander("📍 Preferred Locations"):
                locations = st.text_area("Locations (comma-separated)", ", ".join(job_info.get("Location", []))).split(", ")
            
            with st.expander("🔴 Must to have skills"):
                must_to_have = st.text_area("Must to have (comma-separated)", ", ".join(job_info.get("Must to have", []))).split(", ")
            
            with st.expander("🌟 Good to have skills"):
                good_to_have = st.text_area("Good to have (comma-separated)", ", ".join(job_info.get("Good to have", []))).split(", ")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Save Changes", use_container_width=True):
                    self.update_job_description(skills, project_domains, experience, locations, must_to_have, good_to_have)
                    st.success("✅ Job Description Updated!")
                    st.session_state["editing"] = None

            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state["editing"] = None

        return st.session_state["job_descriptions"]

