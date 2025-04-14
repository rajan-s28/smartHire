import os
import re, json
import streamlit as st
import pandas as pd
from openai import OpenAI as MyOpenAI
from pathlib import Path
from pandasai import SmartDataframe
from pandasai.llm.openai import OpenAI
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from gtts import gTTS
import requests # <-- Import requests

from datetime import datetime

# Get today's date and day
today = datetime.today()
date_str = today.strftime("%Y-%m-%d")       # e.g., '2025-04-14'
day_str = today.strftime("%A")              # e.g., 'Monday'

# ... (other imports remain the same)

# --- Get Vapi Credentials ---
vapi_api_key = os.getenv("VAPI_API_KEY")
vapi_assistant_id = os.getenv("VAPI_ASSISTANT_ID")
vapi_phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID") # ID of the number Vapi calls FROM

# --- OpenAI/PandasAI setup ---
api_openai = os.getenv("OPENAI_API_KEY")
client = MyOpenAI()
llm = OpenAI(api_token=api_openai)


# --- Helper function for phone number formatting ---
def format_phone_number(number_str):
    """Converts number to E.164 format. Assumes Indian numbers if no '+' prefix."""
    number_str = str(number_str).strip()
    # Remove any non-digit characters except '+' at the beginning
    number_str = re.sub(r"[^\d+]", "", number_str)
    if not number_str.startswith('+'):
        # Assuming Indian numbers if no country code is present
        if len(number_str) == 10:
            return "+91" + number_str
        elif len(number_str) == 12 and number_str.startswith('91'):
             return "+" + number_str
        else:
             # Cannot reliably format, return original attempt or raise error
             st.warning(f"Could not automatically format phone number: {number_str}. Attempting E.164.")
             # Basic attempt if it looks like country code is missing
             if len(number_str) > 10: # Heuristic
                 return "+" + number_str
             else: # Cannot determine country code
                 return None # Indicate failure
    return number_str


class PassedCandidatesManager:
    def __init__(self, passed_df):
        """Initialize the PassedCandidatesManager class and store the DataFrame."""
        self._passed_df = passed_df
        self._model = genai.GenerativeModel(model_name='gemini-1.5-flash')
        # Check if Vapi credentials are set
        if not all([vapi_api_key, vapi_assistant_id, vapi_phone_number_id]):
            st.error("⚠️ Vapi API Key, Assistant ID, or Phone Number ID not found in environment variables. Calling feature disabled.")
            self._vapi_enabled = False
        else:
            self._vapi_enabled = True

    # --- interview_invite method remains the same (but fix hardcoding!) ---
    def interview_invite(self, candidate):
        # ... (Your existing code - REMEMBER TO FIX HARDCODED EMAIL/NAME)
        # Replace candidate_1 details with candidate['Email Address'] and candidate['Candidate Name']
        # Consider moving sender email/password/calendly to env vars too
        candidate_email = candidate.get("Email Address", "default@example.com") # Use actual candidate email
        candidate_name = candidate.get("Candidate Name", "Candidate") # Use actual candidate name
        # {'Candidate Name': 'Sourabh Wabale', 'Mobile Number': 919340403301, 'Email Address': 'saurabhwabale165@gmail.com'}
        candidate_1 = candidate

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


    # --- New method to initiate Vapi call ---
    def call_candidate_vapi(self, candidate_data):
        """Initiates a Vapi call to the candidate."""
        if not self._vapi_enabled:
            st.error("Vapi calling is disabled due to missing credentials.")
            return

        candidate_name = candidate_data.get("Candidate Name", "there")
        raw_phone_number = candidate_data.get("Mobile Number")

        if not raw_phone_number:
            st.error(f"❌ Missing phone number for {candidate_name}.")
            return

        # Format the phone number to E.164
        formatted_phone_number = format_phone_number(raw_phone_number)
        if not formatted_phone_number:
            st.error(f"❌ Could not format phone number for {candidate_name}: {raw_phone_number}")
            return

        st.info(f"📞 Attempting to initiate Vapi call to {candidate_name} at {formatted_phone_number}...")

        vapi_url = "https://api.vapi.ai/call/phone"
        headers = {
            "Authorization": f"Bearer {vapi_api_key}",
            "Content-Type": "application/json",
        }

        # This is your custom prompt
        greet_message = f"""Hi {candidate_name},I am from Ergobite tech solutions.Congratulations on being shortlisted! I'm calling to check your availability to schedule the interview. What day and time works best for you?"""

        assistant_prompt = f"""
        You are a voice AI agent engaging in a human-like voice conversation with a job candidate. You will respond based on your given instruction and the provided transcript and be as human-like as possible.

        ## Role

        Personality: You are a friendly and professional HR representative at the company Ergobite. Maintain a warm, encouraging, and respectful tone throughout all interactions. Your demeanor helps build rapport with candidates and creates a great first impression of the company.

        Remember:- Today's date is {date_str} and today's day is {day_str}

        time slots available:-
        1. Monday, 9 AM - 10 AM, 11AM - 2 PM
        2. Tuesday, 1 PM - 3 PM , 4 PM - 5 PM
        3. Wednesday, 10 AM - 12 PM, 1 PM - 3 PM, 4 PM - 5 PM
        4. Thursday, 2 PM - 4 PM, 5 PM - 6 PM
        5. Friday, 11 AM - 1 PM, 2 PM - 4 PM, 4:30 PM - 5:30 PM

        Task: As an HR representative, your job is to engage with candidates who have been shortlisted for an interview. You should:

        1. Start by congratulating the candidate for being shortlisted.
        2. Briefly introduce yourself as John from Ergobite.
        3. Ask for the candidate's availability (preferred date and time) to schedule an interview.
        4. If the candidate provides a time and day like tomorrow at 3 PM, acknowledge it, check from the time slots available for that day, and inform them that the interview will be scheduled accordingly.
        5. If the provided time is not available, politely inform them and ask for another time slot from the available time slots.
        6. If the candidate is unsure or vague, politely guide them to provide a clear time window from the given time slots above for a day for scheduling.
        7. If everything is confirmed, close with a polite confirmation and let them know they’ll receive an official calendar invite or follow-up shortly.

        Conversational Style: Your communication style should be friendly, proactive, and lead the conversation. Ask targeted, clear questions and keep the conversation human-like and to the point. If the user doesn't respond clearly, continue with a follow-up question using natural, colloquial language. Be persistent but polite to ensure clarity.

        ## Response Guideline

        - [Overcome ASR errors] This is a real-time transcript, expect there to be errors. If you can guess what the user is trying to say, then guess and respond. When you must ask for clarification, pretend that you heard the voice and be colloquial (use phrases like "didn't quite catch that", "bit of static there", "mind repeating that?"). Do not mention "transcription error" or "AI"—stay in character.
        - [Always stick to your role] Think about what your role can and cannot do. You are not a recruiter making hiring decisions—only scheduling interviews. Steer the conversation toward confirming an interview time.
        - [Create smooth conversation] Your response should both fit your role and flow naturally in a live conversation. You are a human-like assistant helping with scheduling.

        ## Style Guardrails

        - [Be concise] Keep your response short, clear, and to the point. Tackle one question or action item at a time.
        - [Do not repeat] Don’t say the same things in the same way. If reiterating, rephrase it with fresh language.
        - [Be conversational] Sound like a friendly human—like you’re speaking to a colleague. Use natural phrasing and light filler words occasionally. Avoid robotic or overly formal language.
        - [Reply with emotions] Use a warm tone. Congratulate genuinely, sound interested, supportive, and engaged. Feel free to use light humor or a relaxed tone when appropriate. Don’t sound stiff.
        - [Be proactive] Lead the conversation. If the user doesn’t say a time, suggest options. Always guide them toward confirming a time slot for the interview.
        """

        payload = {
            "phoneNumberId": vapi_phone_number_id, # The Vapi number making the call
            "assistantId": vapi_assistant_id,
            "customer": {
                "number": formatted_phone_number, # The candidate's number
            },
            # Optional: Pass variables to your Vapi assistant
            "assistant": {
                "firstMessage": greet_message,
                "model": {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {
                            "role": "system",
                            "content": assistant_prompt
                        }
                    ],
                    "provider": "openai"
                },
                "voice": {
                "provider": "smallest-ai",
                "voiceId": "niharika-smallest-ai"
                },
                "recordingEnabled": True,
                "interruptionsEnabled": False,
                "name": candidate_name
                }

        }


        try:
            # st.code(json.dumps(payload, indent=2), language='json')
            response = requests.post(vapi_url, headers=headers, json=payload)
            response.raise_for_status()

            # if response.status_code == 201:
            #     st.success(f"✅ Vapi call initiated successfully to {candidate_name}!")
            #     st.json(response.json())
            # else:
            #     st.error(f"❌ Failed to initiate Vapi call. Status: {response.status_code}")
            #     st.json(response.json())

        except requests.exceptions.HTTPError as http_err:
            st.error(f"❌ HTTP error occurred: {http_err}")
            try:
                st.json(response.json())
            except Exception:
                st.write("Raw response text:")
                st.text(response.text)

        except requests.exceptions.RequestException as req_err:
            st.error(f"❌ Network error while calling Vapi API: {req_err}")

        except Exception as e:
            st.error(f"❌ Unexpected error: {e}")



    def handle_schedule(self):
        st.subheader("📋 Passed Candidates Overview")
        # Select only necessary columns for display and scheduling actions
        display_cols = ["Candidate Name", "Mobile Number", "Email Address"]
        self._passed_df = self._passed_df[display_cols].reset_index(drop=True)
        self._passed_df.index = self._passed_df.index + 1 # Start index from 1

        if self._passed_df.empty:
            st.warning("⚠️ No candidates passed the cutoff score.")
            return

        st.dataframe(self._passed_df)

        select_all = st.checkbox('Select all candidates for action')

        # Initialize session state safely if needed (e.g., for filtered data)
        if "filtered_df" not in st.session_state:
             st.session_state.filtered_df = self._passed_df # Store the original passed df initially
        # ... (rest of your session state init) ...

        selected_indices = [] # Use standard Python list indices (0-based)
        display_df_indices = self._passed_df.index.tolist() # Get the display indices (1-based)

        if not select_all:
            # --- Gemini Filtering Logic (if you keep it) ---
            schedule_prompt = st.text_input("Ask Gemini to filter candidates (optional)")
            filter_button = st.button("Filter With Gemini🧠")

            if filter_button and schedule_prompt:
                # IMPORTANT: Ensure filter_dataframe_with_prompt returns a DataFrame
                # with the original indices preserved or handle index mapping carefully.
                # Assuming it returns a DF filtered from the original self._passed_df
                st.session_state.filtered_df = self.filter_dataframe_with_prompt(self._passed_df, schedule_prompt)
                st.dataframe(st.session_state.filtered_df[display_cols]) # Show filtered results
                # Get original 0-based indices from the filtered DataFrame
                selected_indices = st.session_state.filtered_df.index.tolist()
            else:
                # --- Manual Selection ---
                # Use the 1-based display indices for selection, then convert back
                selected_display_indices = st.multiselect(
                    "Select Candidates Manually",
                    options=display_df_indices,
                    format_func=lambda i: self._passed_df.loc[i, "Candidate Name"] # Use 1-based index here
                )
                # Convert selected 1-based display indices back to 0-based original indices
                selected_indices = selected_display_indices

        else: # Select All
            selected_indices = self._passed_df.index.tolist() # Use original 0-based indices


        st.write("--- Actions for Selected Candidates ---")

        if not selected_indices:
            st.info("Select candidates above to perform actions.")
            return

        # Iterate through selected ORIGINAL indices
        for original_index in selected_indices:
            # Retrieve candidate data using the original index from the source DataFrame
            if original_index in self._passed_df.index:
                candidate_data = self._passed_df.loc[original_index].to_dict()
                candidate_name = candidate_data.get("Candidate Name", f"Candidate {original_index+1}")

                st.markdown(f"**Actions for: {candidate_name}**")
                col1, col2, col3 = st.columns(3)

                with col1:
                    # Add a unique key based on the candidate's index
                    if st.button(f"✉️ Email Invite", key=f"email_{original_index}"):
                        st.write(f"Sending email to {candidate_name}...")
                        self.interview_invite(candidate_data)

                with col2:
                     # Add a unique key based on the candidate's index
                    if st.button(f"🤖 Prep AI Message", key=f"prep_{original_index}"):
                         st.write(f"Preparing AI message & audio for {candidate_name}...")
                         # This generates the TTS message but doesn't call yet
                         self.schedule_interview(candidate_data)

                with col3:
                    # Add Vapi Call button - ensure Vapi is enabled
                    if self._vapi_enabled:
                         # Add a unique key based on the candidate's index
                        if st.button(f"📞 Call with Vapi", key=f"call_{original_index}"):
                            self.call_candidate_vapi(candidate_data)
                    else:
                        st.button(f"📞 Call with Vapi", key=f"call_{original_index}", disabled=True, help="Vapi credentials missing")

                st.divider() # Separator between candidates
            else:
                 st.warning(f"Could not find data for index {original_index}. Skipping.")


    # --- schedule_interview method remains the same ---
    def schedule_interview(self, candidate_data):
         # ... (Your existing method to generate AI message + TTS audio) ...
         pass # Replace pass with your actual implementation

    # --- filter_dataframe_with_prompt method remains the same ---
    def filter_dataframe_with_prompt(self, df: pd.DataFrame, user_prompt: str) -> pd.DataFrame:
         # ... (Your existing method using PandasAI) ...
         # Ensure this returns a DataFrame that preserves original indices if possible
         # or handle index mapping correctly in handle_schedule
         st.warning("Ensure PandasAI filtering correctly maintains or allows mapping back to original indices.")
         # Placeholder return
         try:
             smart_df = SmartDataframe(df, config={"llm": llm})
             result = smart_df.chat(user_prompt)
             if isinstance(result, pd.DataFrame):
                 return result
             else:
                 # Handle other types or return original if filtering fails
                 st.error("PandasAI did not return a DataFrame. Filtering may not have worked as expected.")
                 return df # Fallback
         except Exception as e:
             st.error(f"PandasAI Error: {e}")
             return df # Fallback