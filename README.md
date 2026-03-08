**Inspiration**

Over 30% of 911 calls take over 25+ seconds on an elevator message. This can lead to missed 911 calls,
especially in a shortage of 911 operators during an accident. Vigil is a solution for this because it will help take
911 calls and gather information for operators when they decide to take on the call.

**How we built it**

  1. Twillio in order to create a temporary phone number for testing our calls
  2. Ngroq helps create a bridge between our local server and a public endpoint that can send Webhooks to.
  3. Next.JS and FastAPI to help create the frontend and backend of our website

**How to start it?**

1. Run npm install
2. Run the following commands in this order:
  a. ngrok http 8000
  b. uv run uvicorn main:app --port 8000 --reload
  c. npm run dev

**Challenges we ran into**

We ran into challenges with our map. More specifically, when the speech to text was trying to extract the location, our map wasn't creating the pin
correctly. Sometimes, it wouldn't load in the correct pin, or sometimes it wouldn't just load in a pin at all for the location. Also, the speech to text was sometimes inaccurate and wasn't picking up on
the locations correctly. Also, we tried to implement OAuth using a phone number in order to help the operator log in, but we were having issues with trying to sync the ports between
Ngroq, Next.JS, and our backend. Due to these struggles, we ended up scrapping it altogether.

**Accomplishments**

We were able to create a software that can help gather information about a disaster and also give important information to the operator who needs to take the call. 
