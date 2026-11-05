# Project Hyrule Together: Native Co-op & Custom Skins Roadmap

See the complete architectural design and network packet diagrams in the project documentation.

## Pillars:
1. **Puppet Actor Factory:** Spawning and controlling remote Link clone instances.
2. **Native UDP Network Pipeline (ENet / WinSock):** 60–120 Hz state replication with Hermite dead-reckoning extrapolation.
3. **Equipment & Attachment Bone Sockets:** Real-time synchronization of weapons, shields, bows, and paraglider.
4. **Custom Skins & Material Override:** Client-side model and texture swapping (Zelda, Dark Link, custom armor).
5. **Zonai Contraption Sync:** Ultrahand attachment tree and joint replication across players.
6. **Lobby & Matchmaking:** Direct IP & Room-Code lobby manager inside `TotKLauncher.py`.

*Scheduled for development kickoff alongside DRS.*
