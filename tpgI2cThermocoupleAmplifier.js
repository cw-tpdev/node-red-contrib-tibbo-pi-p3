module.exports = function (RED) {
    "use strict";

    // TP Grove - I2C Thermocouple Amplifier

    var TpCommon = require('./tpCommon');

    function TPG_I2cThermocoupleAmplifier_Node(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tpgI2cThermocoupleAmplifier", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput(function (msg, payload) {
            try {
                msg.payload = parseFloat(payload);
            } catch (e) {
                msg.payload = null;
            }
            node.send(msg);

        });

    }
    RED.nodes.registerType("I2cThermocoupleAmplifier", TPG_I2cThermocoupleAmplifier_Node);
}
