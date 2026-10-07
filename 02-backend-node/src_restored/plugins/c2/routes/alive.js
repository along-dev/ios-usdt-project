export async function aliveRoute(fastify) {
    fastify.get('/vhx', async (request, reply) => {
        reply.header('Cache-Control', 'no-cache');
        return 'OK';
    });
}
//# sourceMappingURL=alive.js.map