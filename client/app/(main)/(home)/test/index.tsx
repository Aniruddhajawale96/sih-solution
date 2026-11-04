import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import React, { useEffect, useState } from "react";
import {
  getWorstWeatherNext300Days,
  WorstWeatherDay,
} from "@/lib/api/weather/getWorstWeatherData";

const Test = () => {
  const [data, setData] = useState<WorstWeatherDay[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const data = await getWorstWeatherNext300Days();
      console.log(data);
      if (data) setData(data);
      else console.log("no data");
      setLoading(false);
    };
    load();
  }, []);
  return (
    <View style={{ flex: 1 }}>
      {loading ? (
        <View
          style={[
            StyleSheet.absoluteFill,
            { justifyContent: "center", alignItems: "center" },
          ]}
        >
          <ActivityIndicator size={"large"} />
        </View>
      ) : (
        <>
          {data.length === 0 ? (
            <Text>no major events</Text>
          ) : (
            <ScrollView>
              {data.map((item, index) => (
                <>
                  <View
                    key={index}
                    style={{
                      marginVertical: 10,
                      backgroundColor: "#e5e5e5",
                      padding: 15,
                    }}
                  >
                    <Text>
                      {new Date(item.date).toLocaleDateString("en-In")}
                    </Text>
                    <Text>severity: {item.severity}</Text>
                    <Text>{item.condition}</Text>
                    <Text>maxWindKph: {item.maxWindKph}</Text>
                  </View>
                </>
              ))}
            </ScrollView>
          )}
        </>
      )}
    </View>
  );
};

export default Test;

const styles = StyleSheet.create({});
