async function sendMsg() {
  console.log("✅ chatbot.js successfully loaded!");

  
    const input = document.getElementById("userInput");
  const chatbox = document.getElementById("chatbox");
  const msg = input.value.trim();
  if (!msg) return;

  chatbox.innerHTML += `<div class='user-msg'>${msg}</div>`;
  input.value = "";

  const res = await fetch("/api/chat", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ message: msg })
  });
  const data = await res.json();

  if (data.results) {
    chatbox.innerHTML += `<div class='bot-msg'><p>${data.reply}</p><div class='deck-grid'>${data.results.map(c => `
      <div class='champ-card'>
        <img src="/static/img/champions/${c.icon}" alt="${c.name}">
        <span class='name'>${c.name}</span>
        <span class='cost'>${c.cost}코</span>
      </div>`).join('')}</div></div>`;
  } else {
    chatbox.innerHTML += `<div class='bot-msg'>${data.reply}</div>`;
  }

  chatbox.scrollTop = chatbox.scrollHeight;
}
