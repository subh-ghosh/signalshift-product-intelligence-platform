import { useNavigate } from "react-router-dom"
import { useState } from "react"

export default function Login(){

  const navigate = useNavigate()

  const [email,setEmail] = useState("")
  const [password,setPassword] = useState("")
  const [error,setError] = useState("")

  const handleLogin = () => {

    const validEmail = "netflix_admin@signalshift.com"
    const validPassword = "admin123"

    if(email === validEmail && password === validPassword){

      localStorage.setItem("token","demo-user")

      navigate("/dashboard")

    }else{

      setError("Invalid credentials")

    }
  }

  return(

    <div style={{padding:"40px"}}>

      <h1>Netflix Manager Login</h1>

      <div>

        <input
          type="text"
          placeholder="Email"
          value={email}
          onChange={(e)=>setEmail(e.target.value)}
        />

      </div>

      <div style={{marginTop:"10px"}}>

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e)=>setPassword(e.target.value)}
        />

      </div>

      <div style={{marginTop:"10px"}}>

        <button onClick={handleLogin}>
          Login
        </button>

      </div>

      {error && <p style={{color:"red"}}>{error}</p>}

    </div>

  )
}