const { PASSWORD, send, creaCookie, autenticato, leggiCorpo } = require("./_lib");

module.exports = async (req, res) => {
  if (req.method === "GET") return send(res, 200, { autenticato: autenticato(req), protetto: !!PASSWORD });
  if (req.method === "DELETE") {
    res.setHeader("Set-Cookie", "tvm=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0");
    return send(res, 200, { ok: true });
  }
  const { password } = await leggiCorpo(req);
  if (!PASSWORD || password === PASSWORD) {
    res.setHeader("Set-Cookie", creaCookie());
    return send(res, 200, { ok: true });
  }
  await new Promise((r) => setTimeout(r, 800)); // rallenta i tentativi
  return send(res, 401, { errore: "Password non corretta" });
};
