export default function IssueReviews({issue, reviews}){

  if(!issue) return <p>Select an issue to see related reviews.</p>

  return(

    <div style={{marginTop:"20px"}}>

      <h3>Reviews for: {issue}</h3>

      <ul>

        {reviews.map((r,i)=>(
          <li key={i} style={{marginBottom:"8px"}}>
            {r}
          </li>
        ))}

      </ul>

    </div>

  )

}