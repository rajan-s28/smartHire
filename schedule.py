import os
import re, json
import streamlit as st
import pandas as pd
from pandasai import SmartDataframe
from pandasai.llm.openai import OpenAI  # or other LLMs like HuggingFace, GooglePalm, etc.

import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from gtts import gTTS
# from TTS.api import TTS  # Import TTS
# tts = TTS()
# available_models = tts.list_models()
# print(available_models)
api_openai= os.getenv("OPENAI_API_KEY")
print("API Key:", api_openai)

# Setup LLM
llm = OpenAI(api_token=api_openai)

# Wrap your DataFrame
# smart_df = SmartDataframe(df, config={"llm": llm})

# # Ask your prompt
# result = smart_df.chat("List candidates whose score is above 90")

class PassedCandidatesManager:
    def __init__(self, passed_df):
        """Initialize the PassedCandidatesManager class and store the DataFrame in session state."""
        self._passed_df = passed_df
        self._model = genai.GenerativeModel(model_name='gemini-1.5-flash')

    def interview_invite(self, candidate):
        candidate_1 = {'Candidate Name': 'Sourabh Wabale', 'Mobile Number': 919340403301, 'Email Address': 'saurabhwabale165@gmail.com'}

        # Your Calendly link
        calendly_link = "https://calendly.com/rajan-s-ergobite/30min"

        # Email config
        sender_email = "thakurrajanpratap@gmail.com"
        sender_password = "mhqhybvjpfgpylzi"

        # SMTP server details
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        try:
            # Connect to SMTP
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)

            # Create email
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = candidate_1["Email Address"]
            msg["Subject"] = "Interview Invitation from Ergobite"

            body = f"""
            Hi {candidate_1['Candidate Name']},

            Congratulations! You've been shortlisted for the next round.

            Please use the link below to schedule your interview:
            {calendly_link}

            Looking forward to speaking with you!

            Best regards,  
            Team Ergobite
            """

            msg.attach(MIMEText(body, "plain"))
            server.sendmail(sender_email, candidate_1["Email Address"], msg.as_string())
            server.quit()

            # Streamlit UI update
            st.success(f"✅ Email sent to **{candidate_1['Email Address']}** successfully!")
            st.markdown(f"### 📅 [Click here to select interview slot]({calendly_link})")

        except smtplib.SMTPAuthenticationError:
            st.error("❌ Email sending failed! SMTP Authentication Error. Check credentials.")
        except Exception as e:
            st.error(f"❌ Email sending failed! Error: {e}")
        
    def handle_schedule(self):
        st.subheader("📋 Passed Candidates Overview")           
        orignal_df = self._passed_df[["Candidate Name", "Mobile Number", "Email Address"]].reset_index(drop=True)
        orignal_df.index = orignal_df.index + 1

        if orignal_df.empty:
            st.warning("⚠️ No candidates passed the cutoff score.")
            return

        st.dataframe(orignal_df)

        select_all = st.checkbox('Schedule for all candidates')
        schedule_prompt = st.text_input("Ask Gemini")
        filter_button = st.button("Filter With Gemini🧠")

        # ✅ Initialize session state safely
        if "filtered_df" not in st.session_state:
            st.session_state.filtered_df = self._passed_df
        if "filtered" not in st.session_state:
            st.session_state.filtered = False
        
        if not select_all:
            # Filter button below prompt
            if filter_button and schedule_prompt:

                st.session_state.filtered_df = self.filter_dataframe_with_prompt(self._passed_df, schedule_prompt)
                st.session_state.filtered = True
                st.dataframe(st.session_state.filtered_df)
                selected_indexs = st.session_state.filtered_df.index.tolist()
            else:
                selected_indexs = st.multiselect(
                    "Select Candidate", 
                    self._passed_df.index,
                    format_func=lambda i: self._passed_df.loc[i, "Candidate Name"]
                )
        else:
            selected_indexs = self._passed_df.index.tolist()

        filtered_df = st.session_state.filtered_df
        if st.button("📅 Schedule Interview"):
            for index in selected_indexs:
                st.write(f"Selected Candidate: {filtered_df.loc[index, 'Candidate Name']}")
                selected_candidate = filtered_df.loc[index].to_dict()
                self.schedule_interview(selected_candidate)
                self.interview_invite(selected_candidate)

    def schedule_interview(self, candidate_data):
        """Schedules an interview and asks for the candidate's preferred time via Gemini AI."""
        
        # Step 1: Generate AI-Powered Scheduling Message
        scheduling_prompt = f"""
        You are an HR assistant. The candidate below has been shortlisted for an interview.
        Please ask them at what day and time they are free this week for interview.

        Candidate Details:
        - Name: {candidate_data['Candidate Name']}


        Note: Mobile Number given is of the candidate and will be used to call him do not include it in response

        Response format (Example):
        {{
            "Message": "Dear [Candidate Name], congratulations on being shortlisted! Please share your available time slots for an interview.",
            "Preferred Time": "Candidate’s response: 10:00 AM - 11:00 AM on April 5th"
        }}
        """

        response = self._model.generate_content(scheduling_prompt)

        # Step 2: Parse AI Response
        try:
            json_response = re.search(r"\{.*\}", response.text, re.DOTALL).group()
            interview_details = json.loads(json_response)
            scheduling_message = interview_details["Message"]
        except Exception as e:
            interview_details = {
                "Message": "⚠️ Failed to get response from AI. Please contact the candidate manually.",
                "Preferred Time": "N/A"
            }

        # Step 3: Convert Text to Speech
        tts = gTTS(text=scheduling_message, lang='en')
        output_audio_path = "output.mp3"
        # tts = TTS(model_name="tts_models/en/multi-dataset/vits", progress_bar=False)
        # # tts = TTS(model_name=tts_model, progress_bar=False)
        # output_audio_path = "output.mp3"
        # print("###################",tts.speakers)
        # speaker_id = "speaker_indian"
    
        # tts.tts_to_file(text=scheduling_message, file_path=output_audio_path, speaker=speaker_id)
        # tts.save(output_audio_path)

        print("✅ Speech saved as output.mp3")

        # Step 4: Display Confirmation in Streamlit
        st.success(f"📅 Interview scheduled for {candidate_data['Candidate Name']}")
        st.write("📄 Interview Details:")
        st.json(interview_details)

        # Step 5: Play the Generated Speech in Streamlit
        st.audio(output_audio_path, format="audio/mp3")

    def filter_dataframe_with_prompt(self, df: pd.DataFrame, user_prompt: str) -> pd.DataFrame:
        try:
            # Initialize LLM with your API key
            llm = OpenAI(api_token=api_openai)  # Replace with your key or use env var

            # Create a SmartDataframe instance
            smart_df = SmartDataframe(df, config={"llm": llm})

            # Run the user prompt against the SmartDataframe
            result = smart_df.chat(user_prompt)

            # Handle and return appropriate format
            if isinstance(result, pd.DataFrame):
                return result

            if isinstance(result, list) and isinstance(result[0], dict):
                return pd.DataFrame(result)

            if isinstance(result, list):
                return pd.DataFrame(result, columns=["Mobile Number"])

            st.warning("🤔 Couldn't interpret the LLM output as a table. Returning original DataFrame.")
            return df

        except Exception as e:
            st.error(f"⚠️ PandasAI returned an error: {e}")
            return df