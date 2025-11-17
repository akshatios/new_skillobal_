registerAndSignInDocumentation = """
**Flow: User Sign-Up and Sign-In (Part 1)**

**Purpose of this API:**
1. Accept a user’s email address and send a one-time passcode (OTP) to it.
2. The OTP remains valid for 15 minutes.
3. Users may request a new OTP, but only after waiting 1 minute.

**Code Explanation:**
1. Receive the email address as input.
2. Query the `verificationEmail` collection to see if the same email has requested an OTP within the last 1 minute.
   - If **yes**, return an error: “Please wait 1 minute before requesting again.” 
   - If **no**, proceed to step 3.
3. Generate a new OTP.
4. Send the OTP to the user’s email.
5. Store the OTP in the `verificationEmail` collection with fields:
   - `email`: the user’s email address  
   - `otp`: the generated passcode  
   - `createdTime`: created time timestamp  
   - `isUsed`: set to `False`
"""

genreListDocumentation = """
**Flow: Standalone API with Multiple Uses**

**Purpose of this API:**
1. Fetch and return a list of all available genres.

**Use Cases:**
1. **Genre Selection Flow**  
   - Allows users to select one or more genres from the list.
2. **Movie Filtering Flow**  
   - Enables users to filter movies based on selected genres.

**Code Explanation:**
1. Query the `genres` collection in the database to retrieve all genre available.
2. Return the list of genres as the API response.
"""

genreSelectorDocumentation = """
**Flow: User Genre Selection Flow (Part 2)**  
- **Part 1:** `/user/genreList`

**Purpose of this API:**
1. Accept the user’s selected genres and save them to the database.

**Code Explanation:**
1. Receive `selectedGenres` as a list of genre IDs from the user.
2. Validate the genre IDs to ensure they exist in the `genres` collection.
3. If all genre IDs are valid:
   - Save the selected genres in the `users` collection, associated with the user's profile.

**Note:**
1. If user hit this api twice the new selected genres will replace the old ones as this api works like update not as append.
"""

languageListDocumentation ="""
**Flow: Standalone API**

**Purpose of this API:**
1. Fetch and return a list of all available langauges.

**Use Cases:**
1. **Langauges Selection Flow**  
   - Allows users to select one or more Langauges from the list.

**Code Explanation:**
1. Query the `languages` collection in the database to retrieve all languages available.
2. Return the list of languages as the API response.
"""

languageSelectorDocumentation ="""
**Flow: User languages Selection Flow (Part 2)**  
- **Part 1:** `/user/languageList`

**Purpose of this API:**
1. Accept the user’s selected languages and save them to the database.

**Code Explanation:**
1. Receive `selectedLanguages` as a list of languages IDs from the user.
2. Validate the languages IDs to ensure they exist in the `languages` collection.
3. If all languages IDs are valid:
   - Save the selected languages in the `users` collection, associated with the user's profile.

**Note:**
1. If user hit this api twice the new selected languages will replace the old ones as this api works like update not as append.
"""

trendingMoviesDocumentation = """
**Flow: Standalone API With Multiple Functionalities**

**Purpose of this API:**
1. **If `genreID` == "all"**  
   - Return a list of the top 10 most-viewed movies across all genres.
2. **If `genreID` != "all"**  
   - Return a list of the top 10 most-viewed movies filtered by the specified genre.

**Code Explanation:**
1. Filter movies based on visibility and the provided genre ID (`all` or a specific genre).
2. Use a database aggregation pipeline to:
   - Fetch related shorts and calculate total views (movie views + short views).
   - Sort movies by overall views and limit the results to the top 10.
3. Encode file locations for the movies before returning the response.
4. Handle exceptions and return appropriate responses, including an empty list if no movies are found.

**Note:**
1. **Views** refers to the sum of the movie’s direct views and the number of reaction of its related short clips.
2. Multiple functionality Flag!!!
"""

trendingTrailersDocumentation ="""
**Flow: Standalone API**

**Purpose of this API:**
1. Fetch and return the top 10 most-viewed movie trailers and their associated shorts.

**Use Cases:**
1. Display trending trailers on the dedicated section.
2. Allow users to explore popular trailers along with their related short clips.

**Code Explanation:**
1. Query the database to fetch visible trailers, sorted by views in descending order.
2. Include related shorts using a `lookup` operation, excluding advertisements and non-visible shorts.
3. Group results by trailer ID to aggregate trailer details and their associated shorts.
4. Limit the results to the top 10 trailers.
5. Encode file paths for trailers and return the data in the desired format.

**Note:**
1. Shorts are fetched and included only fi they are marked as `visible` and are not ads.
"""

getUserDetailsDocumentation = """
**Flow: Standalone API**

**Purpose of this API:**
1. Fetch and return detailed information about a specific user.

**Code Explanation:**
1. Match the user in the database using their unique ID.
2. Fetch related data such as:
   - Selected genres and languages, including their names and icons.
   - User's profile image, if available.
   - Device details, formatted with timestamps.
3. Aggregate and structure the user data with additional computed fields (e.g., formatted timestamps, user preferences).
4. Return the structured user details or an error message if the user is not found.
"""

editUserDetailsDocumentation = """
**Flow: Standalone API with Multiple Functionalities**

**Purpose of this API:**
1. If `ext == "delete"`  
   - Remove the user image from the `userProfileImage` collection.  
   - Update the remaining user fields in the `users` collection.  
2. If `ext != "delete"`  
   - Upsert (insert or update) the user image in the `userProfileImage` collection.  
   - Update the remaining user fields in the `users` collection.  

**Some Use Cases:**
1. User updates profile information without changing their image.  
2. User updates both profile details and uploads a new image.  
3. User deletes their existing profile image while updating other details.  

**Code Explanation:**
- Validate that `name`, `email`, `gender`, and `mobile` are provided and correctly formatted.  
- Update the user’s basic details in `users_collection`.  
- Depending on `ext`:
  - `"delete"`: delete the image document for this user.  
  - otherwise: upsert the new image data (`file` + `ext`) into `userProfileImage`.  
- Return a success message, or an error if any step fails.  

**Note:**
- This single endpoint handles both image deletion and image updates alongside profile edits.
- Multiple functionality Flag!!!
"""

searchItemDocumentation = """
**Flow: Standalone API**

**Purpose of this API:**
1. Search for movies by name (case-insensitive) and return matching results.

**Code Explanation:**
1. Ensure the `name` query parameter is provided and non-empty.  
2. Use a case-insensitive regex match on the `name` field in `movies_collection`.  
3. Project each movie’s `_id`, `name`, and `fileLocation`.  
4. Encode the file paths with `encode_file_location`.  
5. Return the list of matching movies—or an empty list with a “no data found” message if none match.
"""

checkInTaskDocumentation = """
**Flow: User Task Completion Flow (Part 1)**

**Purpose of this API:**
1. Fetch and return all check-in tasks assigned to the user.

**Use Cases:**
1. Display daily check-in tasks on the user’s dashboard.
2. Allow users to see which tasks they can complete for points.

**Code Explanation:**
1. Filter `dailyCheckInTask_collection` for records where `assignedUser` matches the current user.  
2. Convert the string `assignedTaskId` into an `ObjectId` for lookup.  
3. Lookup the corresponding task details in `checkInPoints` and merge them with the task record.  
4. Format each task with fields: `taskId`, `status`, `obtainable`, `Day`, `title`, and `allocatedPoints`.  
5. Return the list of tasks or a “no task found” message if the list is empty.
"""

collectCheckInDocumentation = """
**Flow: User Task Completion Flow (Part 2)**  
- **Part 1:** `/user/checkInTask`

**Purpose of this API:**
1. Collect and credit points for a pending check-in task.

**Code Explanation:**
1. Validate `taskId` and authenticated user.  
2. Verify the task exists, is assigned to the user, and is still pending.  
3. Check that the current date is on or after the task’s obtainable date.  
4. Retrieve the task’s point value from `checkInPoints`.  
5. In a database transaction:
   - Mark the task as completed in `dailyCheckInTask_collection`.  
   - Increment the user’s `allocatedPoints` in `users_collection`.  
6. Return a success message with the number of points awarded, or an error if any step fails.
"""

markBookMarkDocumentation = """
**Flow: Multiple Functionalities API + User Shorts Bookmark Flow (Part 1)**

**Purpose of this API:**
1. Toggle a short video in the user’s bookmarks:
   - If the short is already bookmarked, remove it.
   - Otherwise, add it to bookmarks and increment the user's total watched count.

**Use Cases:**
1. User saves a favorite short for later viewing.  
2. User removes a previously saved short.  
3. Track how many shorts a user has bookmarked for sorting and UX purposes.

**Code Explanation:**
1. Validate that `shortsId` is present and a valid ObjectId.  
2. Retrieve the user document from `users_collection`.  
3. Check if `shortsId` already exists in the user’s `BookMark` array:
   - **If present**: pull it from `BookMark` and return a “removed” message.  
   - **If absent**: push a new bookmark object (with `shortsId` and `sortParameter`) and increment `totalShortsWatched`; return a “bookmarked” message.  
4. Handle errors and return appropriate HTTP status codes.

**Note:**
1. `sortParameter` is calculated as `user.totalShortsWatched + 1` to maintain bookmark order.
2. Multiple functionality Flag!!!
"""

getBookMarkDocumentation = """
**Flow: User Shorts Bookmark Flow (Part 2)**  
- **Part 1:** `/user/markBookMark`

**Purpose of this API:**
1. Fetch the user's bookmarked shorts.

**Use Cases:**
1. Display the user's saved shorts for easy access.

**Code Explanation:**
1. Match the authenticated user and project their `BookMark` array.  
2. Unwind each bookmark entry and convert `shortsId` to an `ObjectId`.  
3. Lookup the corresponding short details in `shorts_collection`.  
4. Sort bookmarks by `sortParameter` and merge in short fields.  
5. Encode each short’s `fileLocation` before returning the list (or an empty array).
"""

likeVideoDocumentation = """
**Flow: User Shorts Reaction Flow (Part 1)**  

**Purpose of this API:**
1. Record or update the user’s reaction on a short video and increment its view count.

**Use Cases:**
1. Track user engagement by logging reactions (Laugh, Heart, Sad, Clap, Ovation).  

**Code Explanation:**
1. Validate that `shortsId` and `reactionType` are provided and correct.  
2. In a database transaction:
   - Increment the `views` field on the `shorts_collection`.  
   - Upsert the user’s reaction in `userReactionLogs`.  
3. Return a confirmation message or an error if any step fails.
"""

getAdsDocumentation = """
**Flow: Ad Serving Flow**

**Purpose of this API:**
1. Fetch and return ads for a specified route (`path`) and session type.

**Use Cases:**
1. Display banner or interstitial ads on specific pages (e.g., home, video details).  
2. Serve targeted ads based on the user’s session context.

**Code Explanation:**
1. Validate that `path` and `sessionType` are provided.  
2. Normalize `path` by lowercasing and ensuring it starts with `/`.  
3. Query `adsCollection` for documents matching `position` (route) and `sessionType`.  
4. Project the ad fields: `_id`, `type`, `sessionType`, and `provider`.  
5. Return the list of ads or a “no data” message if none are found.

**Note:**
- The `position` field in the database corresponds to the frontend route (e.g., `/home`, `/profile`).
"""

getPackageDocumentation = """
**Flow: Standalone API**

**Purpose of this API:**
1. Fetch and return a list of all available mint packages.

**Use Cases:**
1. Display in-app purchase options to users.  
2. Populate the pricing page or subscription modal with current plans.

**Code Explanation:**
1. Run an aggregation on `mintsPlanCollection` with no filters to retrieve every package.  
2. Project each package’s fields:
   - `_id` (converted to a string)  
   - `Quantity`  
   - `Price`  
   - `__v` (schema version)  
3. Return the resulting list, or an empty array if no plans are found.
"""

googleAuthDocumentation = """User Creation and Login by Google authentication"""

fetchWalletDocumentation = """
**Flow: Standalone API**

**Purpose of this API:**
1. Fetch and return the authenticated user’s wallet points balance.

**Use Cases:**
1. Display the user’s current points in their profile or dashboard.  
2. Validate that the user has sufficient points before allowing point-based actions (e.g., watching video in higher quality).

**Code Explanation:**
1. Retrieve the user’s document by `userId` and project only the `allocatedPoints` field.  
2. If the user is not found (invalid token), return an error.  
3. Otherwise, return the `allocatedPoints` value in the response.
"""

mintsPurchaseHistoryDocumentation = """
**Flow: Mints Purchase History Flow (Part 4)**
   - **Part 1:** `/payments/getUrl`
   - **Part 2.1:** `/payments/success`
   - **Part 2.2:** `/payments/error`
   - **Part 3:** `/payments/verify`

**Purpose of this API:**
1. Fetch and return the user’s mint purchase history.

**Use Cases:**
1. Display a list of past mint transactions in the user’s purchase history section.  
2. Allow users to review transaction details such as date, amount, and status.

**Code Explanation:**
1. Match records in `paidMintsBuyerCollection` where `userId` equals the current user.  
2. Format and project each transaction with:
   - `_id` (as a string)  
   - `txnid` (transaction ID)  
   - `date` (ISO-formatted)  
   - `netAmountDeducted`  
   - `status`  
   - `quantity`  
   - `amount`  
3. Return the list of transactions (or an empty list if none exist).

**Note:**
- Dates are formatted to ISO strings in UTC for frontend consistency.
"""

continueWatchingDocumentation = """
**Flow: User watch history flow (Part 1) with Multiple Functionalities**

**Purpose of this API:**
1. **If `isShortWatchedCompletely` is `True`:**  
   - Mark the current short as fully watched in the user’s history (`shortsHistory`).  
   - Return immediately without further changes.
2. **If `isShortWatchedCompletely` is `False`:**  
   - Record the user’s in-progress timestamp for the current short.  
   - If this is the first time the user watches any short of the movie:
     - Insert a new history document listing all shorts (with initial timestamps and `isWatchedCompletely = False`), set the timestamp for the current short, and initialize `sortParameter`.  
   - Otherwise:
     - Update only the current short’s timestamp and `isWatchedCompletely` flag in the existing history document, and bump `sortParameter`.

**Use Cases:**
1. Resume playback at the last watched position.  
2. Track when each short is fully completed for progress indicators.  
3. Maintain an ordered history of watched shorts across sessions.

**Code Explanation:**
1. Validate required inputs: `moviesId`, `currentShortsId`, `timestamp` (when in-progress), and `isShortWatchedCompletely`.  
2. **Completion path:** update the `isWatchedCompletely` flag for that short.  
3. **Progress path:**  
   - Fetch or create the user’s history for this movie.  
   - In a transaction, insert or update the `shorts` array and increment the user’s `totalShortsWatched`.  
4. Return a message indicating whether history was inserted, updated, or unchanged.

**Note:**
- This endpoint will be called multiple times per short to keep history current (e.g., at different playback times).  
- Uses `sortParameter` for ordering history entries by watch sequence.
- Multiple functionality Flag!!!
"""

getContinueWatchingDocumentation = """
**Flow: User watch history flow (Part 2)**
   - **Part 1:** `/user/continueWatching`

**Purpose of this API:**
1. Fetch and return the authenticated user’s watch history (movies and last watched timestamps).

**Use Cases:**
1. Populate a “Continue Watching” section with the user’s in-progress movies.  
2. Allow users to resume playback from their last watched position.

**Code Explanation:**
1. Match `shrtsHistory` documents for the current user.  
2. Lookup moovie details from `movies` collection and unwind the result.  
3. Sort history entries by `sortParameter` (most recently watched first).  
4. Extract the `timestamp` for the `currentShortsId` from the `shorts` array.  
5. Project each entry to include:
   - `moviesId`, `userId`, `currentShortsId`, `timestamp`  
   - `movieDetail` (name, fileLocation, screenType)  
6. Encode the movie’s `fileLocation` and return the list, or an empty array if none are found.

**Note:**
- This endpoint shows only the most recent position per movie, suitable for “resume” functionality.
"""

unlikeVideoDocumentation = """
**Flow: User Shorts Reaction Flow (Part 2)**  
- **Part 1:** `/user/likeVideo`

**Purpose of this API:**
1. Delete the user’s reaction on a short video and decrement its view count.

**Use Cases:**
1. Allow users to undo a reaction they previously gave.  
2. Maintain accurate view counts when reactions are removed.

**Code Explanation:**
1. Validate that `shortsId` is provided and is a valid ObjectId.  
2. In a database transaction:
   - Remove the user’s reaction document from `userReactionLogs`.  
   - Decrement the `views` field on the corresponding short in `shorts_collection`.  
3. Return a confirmation message or an error if any step fails.
"""

verifyEmailDocumentation ="""
**Flow: User Sign-Up and Sign-In (Part 2)**
   - **Part 1:** `/user/registerAndSignIn`

**Purpose of this API:**
1. Accept a user’s one-time passcode (OTP) and email, verify it, and either sign in or register the user.

**Use Cases:**
1. Confirm email ownership during registration  and also save the user details.  
2. Authenticate existing users via OTP without a password.

**Code Explanation:**
- Validate that `otp` and `email` are provided.  
- Retrieve the OTP record and check:
  - It matches the provided code.
  - It has not been used already.
  - It is not older than 15 minutes.  
- Mark the OTP as used.  
- If the email exists in `users_collection`:
  - Update login status, generate a new token, and return existing user data.  
- Otherwise (new user):
  - In a transaction, save the new user, send a welcome email, generate a token, and return the new user data.

**Note:**
- OTP expires 15 minutes after issuance and can only be used once.
"""
userAppVersionControlDocumentation = """
**Flow: User App Version Control Flow**

**Purpose of this API:**
1. Update the user’s app version.
2. Update the Location based input about the user

**Use Cases:**
1. Update the user app version
2. Update the user location in object LatestGeoLocation and array UserLocationHistory

**Code Explanation:**
1. Get the token and app version form frontend.  
2. Update the user app version and user location.
"""


appleLoginSignupDocumentation=""" 
- Frontend is calling SignInWithApple.getAppleIDCredential(...), requesting email and fullName scopes
- Documentation frontend use - https://pub.dev/packages/sign_in_with_apple/example
- Frontend will get identityToken (JWT) and, only first-time, the raw email + givenName/familyName
- Now Apple can relay a private email address (like w8j3kslq@privaterelay.appleid.com) rather than the user’s real one (so you may not see the “real” email you can message them at).
- Apple doesn’t automatically give every user an @apple.com address the way Google gives everyone an @gmail.com address. Instead, when you create an Apple ID you either:
    - Use an existing third-party email address
        – e.g. youremail@gmail.com, you@outlook.com, you@yourdomain.com -> there email can be send
    - Create an Apple-hosted iCloud email 
        - If you sign up directly for iCloud Mail (or upgrade an Apple ID created with a third-party address), you get an @icloud.com address (or, for very old accounts, @me.com or @mac.com).
        - Here also email can be send
    - Use Apple’s “Private Relay” forwarding address
        - When you opt into “Hide My Email” in Sign in with Apple, Apple gives you a random relay address like w8j3kslq@privaterelay.appleid.com.
        - Mail sent there is forwarded to your real inbox, but you never see the relay address in your Apple ID settings.

# Questions

- Can I send mail to a “private-relay” address and have it land in the user’s real inbox?
    - Yes. Apple’s “Hide My Email” relay addresses are real mailbox forwarders. Mail you send to abc123@privaterelay.appleid.com will be forwarded to the user’s true inbox.
    - Caveat: Apple may throttle or filter unexpected bulk mail—so treat that relay like any address you don’t fully control (opt-in confirmation is best).

- On first authorization, if the user chose “Hide My Email,” do both the identityToken and the Flutter client get the private address?
    - yes

- If the user opts not to hide, you get their real address in both places—forever?
    - Yes. If they choose to share their real email, both the JWT and the client callback include that real address on first sign-in and on every subsequent one.

- Could you ever get a different email from the client than from the JWT?
    - No. Apple’s JWT is the source of truth. The client SDK simply relays what Apple put in the JWT’s email claim.
    - Bottom-line: you can safely ignore credential.email on the client and rely only on the email claim inside the identityToken. You’ll never “miss” an address by doing so.

- Will sub ever change for a given user+app?
    - Never. Apple issues a unique sub (subject) string that is stable for the same user and your specific client-ID (bundle-ID). You can treat it as a permanent social-login key.

# How the security model works

- JWT Signature Verification
    - Apple signs each identityToken with one of their private RSA keys.
    - You fetch Apple’s public keys (the JWKS) from https://appleid.apple.com/auth/keys.
    - By verifying the JWT’s signature against those public keys, you prove the token truly came from Apple and wasn’t forged or tampered with.

- Claim Validation
    - You check iss must equal https://appleid.apple.com.
    - You check aud matches your client-ID (your app’s bundle ID).
    - You check exp > now (token not expired) and optionally iat/nbf

- Trusting the Payload
    - Once the signature and claims check out, you can safely read sub, email, and email_verified and build your own session around them.

- No Dependence on Client
    - Even if a malicious app tried to spoof the client-side API, they can’t forge Apple’s signature. That JWT check is all you need.
"""