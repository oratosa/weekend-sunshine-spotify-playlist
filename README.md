# weekend-sunshine-spotify-playlist

Fetches NHK-FM's Weekend Sunshine broadcast metadata and stores it in Firestore.

## Configuration

Create a Secret Manager secret named `NHK_API_KEY` containing the NHK API key. The
Cloud Function's runtime service account needs:

- Secret Manager Secret Accessor on the `NHK_API_KEY` secret
- Cloud Datastore User on the project

The deployment workflow injects the secret as the `NHK_API_KEY` environment
variable. The deployment workflow injects that secret into the
`NHK_API_KEY` environment variable and deploys the
`fetch_and_save_weekend_sunshine_nhk_identifier_groups` HTTP entry point.

The GitHub Actions repository secrets must include `GCP_PROJECT_ID` in addition
to the Workload Identity and deployment service account secrets.

## Usage

The function fetches the current date in Japan when no date is supplied:

```text
https://REGION-PROJECT_ID.cloudfunctions.net/weekend-sunshine-spotify-playlist
```

To fetch a specific date, pass `date=YYYY-MM-DD`:

```text
https://REGION-PROJECT_ID.cloudfunctions.net/weekend-sunshine-spotify-playlist?date=2026-08-22
```

Matching records are saved to `weekendSunshineNhkIdentifierGroups` using
`radioEpisodeId` as the Firestore Document ID. Repeating the same request
updates the existing document instead of creating a duplicate.
