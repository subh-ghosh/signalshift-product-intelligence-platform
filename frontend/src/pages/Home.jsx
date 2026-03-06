import { useNavigate } from "react-router-dom"

export default function Home(){

  const navigate = useNavigate()

  const selectApp = () => {

    navigate("/login")

  }

  return(

    <div style={{padding:"40px"}}>

      <h1>SignalShift</h1>

      <h2>Select Product</h2>

      <button onClick={selectApp}>
        Netflix
      </button>

    </div>

  )
}