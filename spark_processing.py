import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType


# Initialize logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s:%(funcName)s:%(levelname)s:%(message)s')
logger = logging.getLogger("spark_structured_streaming")


def initialize_spark_session(app_name):
    """
    Initialize the Spark Session with provided configurations.
    
    :param app_name: Name of the spark application.
    :return: Spark session object or None if there's an error.
    """
    try:
        spark = SparkSession \
                .builder \
                .appName(app_name) \
                .getOrCreate()

        spark.sparkContext.setLogLevel("ERROR")
        logger.info('Spark session initialized successfully')
        return spark

    except Exception as e:
        logger.error(f"Spark session initialization failed. Error: {e}")
        return None


def get_streaming_dataframe(spark, brokers, topic):
    """
    Get a streaming dataframe from Kafka.
    
    :param spark: Initialized Spark session.
    :param brokers: Comma-separated list of Kafka brokers.
    :param topic: Kafka topic to subscribe to.
    :return: Dataframe object or None if there's an error.
    """
    try:
        df = spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", brokers) \
            .option("subscribe", topic) \
            .option("delimiter", ",") \
            .option("startingOffsets", "earliest") \
            .load()
        logger.info("Streaming dataframe fetched successfully")
        return df

    except Exception as e:
        logger.warning(f"Failed to fetch streaming dataframe. Error: {e}")
        return None


def transform_streaming_data(df):
    """
    Transform the initial dataframe to get the final structure.
    
    :param df: Initial dataframe with raw data.
    :return: Transformed dataframe.
    """
    schema = StructType([
        StructField("full_name", StringType(), False),
        StructField("gender", StringType(), False),
        StructField("location", StringType(), False),
        StructField("city", StringType(), False),
        StructField("country", StringType(), False),
        StructField("postcode", IntegerType(), False),
        StructField("latitude", FloatType(), False),
        StructField("longitude", FloatType(), False),
        StructField("email", StringType(), False)
    ])

    transformed_df = df.selectExpr("CAST(value AS STRING)") \
        .select(from_json(col("value"), schema).alias("data")) \
        .select("data.*")
    return transformed_df


def initiate_streaming_to_postgresql(df, url, table, user, password):
    """
    Start streaming the transformed data to the specified PostgreSQL database.
    
    :param df: Transformed dataframe.
    :param url: JDBC URL for PostgreSQL.
    :param table: Table name in PostgreSQL.
    :param user: Database user.
    :param password: Database password.
    :return: None
    """
    logger.info("Initiating streaming process...")
    stream_query = (df.writeStream
                    .format("jdbc")
                    .option("url", url)
                    .option("dbtable", table)
                    .option("user", user)
                    .option("password", password)
                    .outputMode("append")
                    .start())
    stream_query.awaitTermination()


def main():
    app_name = "SparkStructuredStreamingToPostgreSQL"
    brokers = "kafka_broker_1:19092,kafka_broker_2:19093,kafka_broker_3:19094"
    topic = "names_topic"
    postgres_url = "jdbc:postgresql://localhost:5432/con-spark"
    postgres_table = "json_table"
    postgres_user = "postgres"
    postgres_password = "128311"

    spark = initialize_spark_session(app_name)
    if spark:
        df = get_streaming_dataframe(spark, brokers, topic)
        if df:
            transformed_df = transform_streaming_data(df)
            initiate_streaming_to_postgresql(transformed_df, postgres_url, postgres_table, postgres_user, postgres_password)


# Execute the main function if this script is run as the main module
if __name__ == '__main__':
    main()