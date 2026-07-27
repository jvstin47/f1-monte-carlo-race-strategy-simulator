import React from 'react';

const TrackSelector = ({ tracks, selectedTrackId, onSelectTrack }) => {
  if (!tracks || Object.keys(tracks).length === 0) {
    return null;
  }

  return (
    <div className="track-selector-grid">
      {Object.entries(tracks).map(([trackId, trackData]) => (
        <div
          key={trackId}
          className={`track-card ${selectedTrackId === trackId ? 'active' : ''}`}
          onClick={() => onSelectTrack(trackId)}
        >
          <div className="track-name">{trackData.name}</div>
          <div className="track-stat">
            <span>Laps:</span>
            <span>{trackData.num_laps}</span>
          </div>
          <div className="track-stat">
            <span>Base Lap:</span>
            <span>{trackData.base_lap_time}s</span>
          </div>
          <div className="track-stat">
            <span>Pit Loss:</span>
            <span>{trackData.pit_stop_time_loss}s</span>
          </div>
        </div>
      ))}
    </div>
  );
};

export default TrackSelector;
