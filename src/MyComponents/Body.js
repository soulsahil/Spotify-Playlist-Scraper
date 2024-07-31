import React, {useState, useEffect} from 'react'
import './styles.css'

export default function Body() {
    useEffect(() => {
        authenticateSpotify();
      }, []);

      const authenticateSpotify = () => {
        fetch('http://localhost:5000', {
          method: 'GET',
        })
          .then(response => response.json())
          .then(data => {
            console.log('Authentication response:', data);
          })
          .catch(error => {
            console.error('Error during authentication:', error);
          });
      };
    
    const[playlistId, setPlaylistId] = useState('');

    const handleSubmit = (event) => {
        event.preventDefault();

        window.location.href = `http://localhost:5000/authenticate?playlistId=${playlistId}`;
        fetch('http://localhost:5000/set_playlist_id',{
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ playlistId }),
        })
            .then(response => response.json())
            .then(data => {
                console.log("Success: ", data)
            })
            .catch(error => {
                console.error("Error", error)
            });
    };

  return (
    <div>
      <form action="" onSubmit={handleSubmit}>
      <input className='search_bar' type="text" placeholder='Search' value={playlistId} onChange={(e) => setPlaylistId(e.target.value)}/>
      <button className='submit_btn' type='submit' >Submit</button>
      </form>
    </div>
  )
}
