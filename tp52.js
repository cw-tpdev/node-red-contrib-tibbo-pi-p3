module.exports = function (RED) {
    "use strict";

    // #52 Four-channel isolated +/-10V ADC

    var TpCommon = require('./tpCommon');

    function TP_52Node(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common 
        var tc = new TpCommon("tp52", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput(function (msg, payload) {
            try {
                msg.payload = JSON.parse(payload);
            } catch (e) {
                msg.payload = null;
            }
            node.send(msg);

        });
    }
    RED.nodes.registerType("Tibbit-#52", TP_52Node);

}
