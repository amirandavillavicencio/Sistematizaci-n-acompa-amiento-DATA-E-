async function init(){
  const res = await fetch('./data/apoyos_consolidados.json')
  const data = await res.json()
  console.log("Datos cargados:", data)
}

init()
