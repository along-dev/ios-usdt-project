export async function telemetryRoute(fastify) {
    fastify.addContentTypeParser('*', (_request, _payload, done) => { done(null); });
    fastify.post('/t', async () => {
        return {};
    });
}
//# sourceMappingURL=telemetry.js.map